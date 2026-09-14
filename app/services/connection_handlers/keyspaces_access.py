"""Keyspaces table data access includes required read-only system metadata."""

from app.models.connection_configs.table_access import KeyspacesTableAccessConfig
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.table_access import TableAccessHandler


class KeyspacesAccessHandler(TableAccessHandler):
    config_model = KeyspacesTableAccessConfig
    resource_type = "aws_keyspaces_keyspace"
    database_name_attribute = "name"
    read_actions = ["cassandra:Select"]
    write_actions = ["cassandra:Modify"]

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="The selected table must be provisioned separately in this keyspace. Use a Cassandra driver with the AWS SigV4 authentication plugin and the exported Region/keyspace/table metadata; connect to the regional Keyspaces endpoint over TLS on port 9142. System-keyspace metadata is readable for driver initialization, including on write connections. Network reachability and any external encryption-key policy remain separate. No service-specific credentials are created.",
            )
        ]

    def supporting_permissions(
        self, connection: ConnectionIR, resource: str
    ) -> ConnectionContribution:
        target, source = connection.target_name, connection.source_name
        variable = f"keyspaces_{target}_system_arn"
        output = "client_system_keyspaces_arn"
        return ConnectionContribution(
            outputs=[
                self._output(
                    target,
                    output,
                    f'format("%s:/keyspace/system*", join(":", slice(split(":", {resource}.arn), 0, 5)))',
                )
            ],
            inputs=[
                ModuleInput(
                    module=source, name=variable, value=f"module.{target}.{output}"
                )
            ],
            iam=[
                self._grant(
                    source,
                    IAMStatement(
                        actions=["cassandra:Select"],
                        resources=["${var." + variable + "}"],
                    ),
                )
            ],
        )
