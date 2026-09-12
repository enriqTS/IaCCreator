"""One source-owned replication configuration with versioned destination references."""

import hashlib

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.replication import S3ReplicationConfig
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ModuleOutput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.kms_references import managed_key


class S3ReplicationHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="The external replication role must trust S3 and have version-read, replication, and applicable source/destination KMS permissions. External destinations require versioning and any bucket policy separately. Live replication applies to new objects; existing objects require S3 Batch Replication.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        source = self._find_instance(connection.source_name, project)
        peers = [
            item
            for item in project.connections
            if item.source_name == source.name
            and item.target_service == ServiceType.S3
            and item.connection_type == "replicates_to"
        ]
        configs = [
            (item, S3ReplicationConfig.model_validate(item.connection_config))
            for item in peers
        ]
        if any(item.target_name == source.name for item, _ in configs):
            self._reject(connection, "A bucket cannot replicate to itself")
        roles = {config.role_arn for _, config in configs}
        if len(roles) != 1:
            self._reject(
                connection, "All replication rules for one source require the same role"
            )
        unique = {}
        for item, config in configs:
            key = (item.target_name, config.prefix)
            if key in unique and unique[key][1] != config:
                self._reject(
                    connection,
                    "Conflicting replication settings for one destination/prefix",
                )
            unique[key] = (item, config)
        role = next(iter(roles))
        source.config.replication_role_arn = role
        result = ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=source.name,
                    name="replication_role_arn",
                    value=self._renderer.render_expression(role),
                    description="External S3 replication role",
                ),
                ModuleInput(
                    module=source.name,
                    name="versioning_enabled",
                    value='"Enabled"',
                    description="Replication requires source versioning",
                ),
            ]
        )
        rules = []
        if source.config.replication_destination_bucket:
            destination = {"bucket": Expr("var.replication_destination_bucket")}
            if source.config.replication_destination_storage_class:
                destination["storage_class"] = Expr(
                    "var.replication_destination_storage_class"
                )
            rules.append(
                {
                    "id": "external",
                    "priority": 0,
                    "status": "Enabled",
                    "filter": {"prefix": ""},
                    "delete_marker_replication": {"status": "Disabled"},
                    "destination": destination,
                }
            )
        for index, key in enumerate(sorted(unique), start=1):
            item, config = unique[key]
            target = self._find_instance(item.target_name, project)
            variable = f"replica_{target.name}_arn"
            result.inputs.extend(
                [
                    ModuleInput(
                        module=source.name,
                        name=variable,
                        value=f"module.{target.name}.replication_bucket_arn",
                        description="Versioned replication destination",
                    ),
                    ModuleInput(
                        module=target.name,
                        name="versioning_enabled",
                        value='"Enabled"',
                        description="Replication requires destination versioning",
                    ),
                ]
            )
            result.outputs.append(
                ModuleOutput(
                    module=target.name,
                    name="replication_bucket_arn",
                    value=f"aws_s3_bucket.{target.name}.arn",
                    description="Bucket ARN available after versioning",
                    depends_on=[f"aws_s3_bucket_versioning.{target.name}_versioning"],
                )
            )
            destination = {"bucket": Expr(f"var.{variable}")}
            replica_key = self._replica_key(item, config, target, project, result)
            rule = {
                "id": "managed-" + hashlib.sha256(repr(key).encode()).hexdigest()[:16],
                "priority": index,
                "status": "Enabled",
                "filter": {"prefix": config.prefix},
                "delete_marker_replication": {"status": "Disabled"},
                "destination": destination,
            }
            if replica_key:
                destination["encryption_configuration"] = {
                    "replica_kms_key_id": replica_key
                }
                rule["source_selection_criteria"] = {
                    "sse_kms_encrypted_objects": {"status": "Enabled"}
                }
            elif managed_key(source.name, project) or source.config.sse_algorithm in {
                "aws:kms",
                "aws:kms:dsse",
            }:
                self._reject(
                    connection,
                    "KMS-encrypted source replication requires a destination KMS key ARN",
                )
            rules.append(rule)
        result.resources.append(
            self._resource(
                source.name,
                "replication.tf",
                self._renderer.render_resource(
                    "aws_s3_bucket_replication_configuration",
                    f"{source.name}_replication",
                    {
                        "bucket": Expr(f"aws_s3_bucket.{source.name}.id"),
                        "role": Expr("var.replication_role_arn"),
                        "rule": rules,
                        "depends_on": Expr(
                            f"[aws_s3_bucket_versioning.{source.name}_versioning]"
                        ),
                    },
                ),
            )
        )
        return result

    def _replica_key(self, connection, config, target, project, result) -> Expr | None:
        key = managed_key(target.name, project)
        external = config.replica_kms_key_arn or target.config.sse_kms_key_id
        if key:
            value = f"module.{key}.key_arn"
        elif external and external.startswith("arn:"):
            value = self._renderer.render_expression(external)
        elif external:
            self._reject(
                connection, "An external replica key must be supplied as a KMS key ARN"
            )
        else:
            return None
        variable = f"replica_{target.name}_{hashlib.sha256(config.prefix.encode()).hexdigest()[:12]}_kms_arn"
        result.inputs.append(
            ModuleInput(
                module=connection.source_name,
                name=variable,
                value=value,
                description="KMS key used to encrypt replicated objects",
            )
        )
        return Expr(f"var.{variable}")

    @staticmethod
    def _reject(connection: ConnectionIR, message: str) -> None:
        raise InvalidConnectionConfigError(
            connection.source_name,
            connection.target_name,
            connection.connection_type,
            [{"loc": ("replication",), "msg": message}],
        )
