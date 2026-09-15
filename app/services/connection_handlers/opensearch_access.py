"""OpenSearch document operations grant HTTP verbs on explicit index paths."""

import hashlib
from typing import Literal

from app.generators.hcl_renderer import Expr
from app.models.connection_configs.opensearch import OpenSearchIndexAccessConfig
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class OpenSearchAccessHandler(BaseConnectionHandler):
    def __init__(self, access: Literal["read", "write"]):
        super().__init__()
        self._operations = (
            [
                (["es:ESHttpGet", "es:ESHttpHead"], ["/_doc/*", "/_search", "/_count"]),
                (["es:ESHttpPost"], ["/_search", "/_count"]),
            ]
            if access == "read"
            else [
                (["es:ESHttpPut"], ["/_doc/*"]),
                (["es:ESHttpPost"], ["/_doc", "/_doc/*", "/_update/*", "/_bulk"]),
                (["es:ESHttpDelete"], ["/_doc/*"]),
            ]
        )

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Uses signed HTTPS requests to the selected index's document/search APIs. Index provisioning, aliases, network access, domain policies, and fine-grained security role mappings remain external. Existing policies can broaden or deny access. Disables rest.action.multi.allow_explicit_index for the entire domain, which affects bulk/multi-index clients and can break Dashboards. Writes include document deletes and index-scoped bulk operations; index and cluster administration are excluded. No credentials are created.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        config = OpenSearchIndexAccessConfig.model_validate(
            connection.connection_config
        )
        domain = self._find_instance(connection.target_name, project)
        domain.config._index_client_access = True
        source, target = connection.source_name, connection.target_name
        resource = f"aws_opensearch_domain.{target}"
        suffix = hashlib.sha256(config.index_name.encode()).hexdigest()[:16]
        binding = f"opensearch_{target}_{suffix}"
        result = ConnectionContribution()
        expressions = {
            "domain_arn": f"{resource}.arn",
            "endpoint": f'format("https://%s", {resource}.endpoint)',
            "region": f'split(":", {resource}.arn)[3]',
        }
        for field, expression in expressions.items():
            output, variable = f"index_client_{field}", f"opensearch_{target}_{field}"
            result.outputs.append(self._output(target, output, expression))
            result.inputs.append(
                ModuleInput(
                    module=source, name=variable, value=f"module.{target}.{output}"
                )
            )
        metadata = {
            "index_name": config.index_name,
            "endpoint": Expr(f"var.opensearch_{target}_endpoint"),
            "region": Expr(f"var.opensearch_{target}_region"),
        }
        result.outputs.append(
            self._output(
                source,
                binding,
                self._renderer.render_expression(metadata),
                "Signed OpenSearch index client configuration",
            )
        )
        prefix = "${var.opensearch_" + target + "_domain_arn}/" + config.index_name
        for actions, paths in self._operations:
            result.iam.append(
                self._grant(
                    source,
                    IAMStatement(
                        actions=actions, resources=[prefix + path for path in paths]
                    ),
                )
            )
        return result
