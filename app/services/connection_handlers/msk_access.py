"""MSK client grants retain cluster UUIDs in topic and group resource ARNs."""

import hashlib
import re
from typing import Literal

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.msk import MskTopicReadConfig, MskTopicWriteConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models.msk_config import MSK_IAM_VERSION_PATTERN
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class MskAccessHandler(BaseConnectionHandler):
    def __init__(self, access: Literal["read", "write"]):
        super().__init__()
        self._access = access

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Enables MSK IAM authentication and TLS-only transport, disabling unauthenticated clients. Application code must use an IAM-capable Kafka client and the exported private bootstrap brokers. Topics, network reachability, cross-account cluster policies, and client deployment remain separate. Reads include joining the selected group and committing its offsets. Writers must disable producer idempotence and omit transactional IDs; transactions, topic administration, and Lambda event-source mappings are not configured. Existing IAM or cluster policies can broaden or deny these grants. No credentials are created.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        model = MskTopicReadConfig if self._access == "read" else MskTopicWriteConfig
        config = model.model_validate(connection.connection_config)
        cluster = self._find_instance(connection.target_name, project)
        service = cluster.config
        if service.kafka_version is None or not re.match(
            MSK_IAM_VERSION_PATTERN, service.kafka_version
        ):
            self._reject(connection, "Select MSK Kafka version 2.7.1 or newer")
        if (
            len(set(service.subnet_ids)) not in {2, 3}
            or len(set(service.subnet_ids)) != len(service.subnet_ids)
            or not service.security_group_ids
            or service.number_of_broker_nodes is None
            or service.number_of_broker_nodes < 1
            or service.number_of_broker_nodes % len(set(service.subnet_ids))
        ):
            self._reject(
                connection,
                "MSK clients require two or three distinct broker subnets, security groups, and a positive broker count divisible by the subnet count",
            )
        service._iam_client_access = True
        source, target = connection.source_name, connection.target_name
        resource = f"aws_msk_cluster.{target}"
        group = config.consumer_group if isinstance(config, MskTopicReadConfig) else ""
        suffix = hashlib.sha256(
            f"{self._access}:{config.topic_name}:{group}".encode()
        ).hexdigest()[:16]
        expressions = {
            "cluster_arn": f"{resource}.arn",
            "topic_arn_prefix": f'replace({resource}.arn, ":cluster/", ":topic/")',
            "bootstrap_brokers": f"{resource}.bootstrap_brokers_sasl_iam",
            "region": f'split(":", {resource}.arn)[3]',
        }
        if group:
            expressions["group_arn_prefix"] = (
                f'replace({resource}.arn, ":cluster/", ":group/")'
            )
        result = ConnectionContribution()
        for field, expression in expressions.items():
            output, variable = f"iam_client_{field}", f"msk_{target}_{field}"
            result.outputs.append(self._output(target, output, expression))
            result.inputs.append(
                ModuleInput(
                    module=source, name=variable, value=f"module.{target}.{output}"
                )
            )
        metadata = {
            "topic_name": config.topic_name,
            "bootstrap_brokers": Expr(f"var.msk_{target}_bootstrap_brokers"),
            "region": Expr(f"var.msk_{target}_region"),
            "security_protocol": "SASL_SSL",
            "sasl_mechanism": "OAUTHBEARER",
        }
        if group:
            metadata["group_id"] = group
        else:
            metadata["enable_idempotence"] = False
        result.outputs.append(
            self._output(
                source,
                f"msk_{target}_{suffix}",
                self._renderer.render_expression(metadata),
                "MSK IAM Kafka client configuration",
            )
        )
        grants = [
            (
                ["kafka-cluster:Connect", "kafka-cluster:DescribeCluster"],
                "${var.msk_" + target + "_cluster_arn}",
            ),
            (
                [
                    "kafka-cluster:DescribeTopic",
                    "kafka-cluster:ReadData" if group else "kafka-cluster:WriteData",
                ],
                "${var.msk_" + target + "_topic_arn_prefix}/" + config.topic_name,
            ),
        ]
        if group:
            grants.append(
                (
                    ["kafka-cluster:DescribeGroup", "kafka-cluster:AlterGroup"],
                    "${var.msk_" + target + "_group_arn_prefix}/" + group,
                )
            )
        for actions, arn in grants:
            result.iam.append(
                self._grant(source, IAMStatement(actions=actions, resources=[arn]))
            )
        return result

    @staticmethod
    def _reject(connection: ConnectionIR, message: str) -> None:
        raise InvalidConnectionConfigError(
            connection.source_name,
            connection.target_name,
            connection.connection_type,
            [{"loc": ("msk",), "msg": message}],
        )
