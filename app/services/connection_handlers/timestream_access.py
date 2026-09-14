"""Timestream table data actions require separate endpoint discovery access."""

from app.models.connection_configs.table_access import TimestreamTableAccessConfig
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ProjectIR,
)
from app.services.connection_handlers.table_access import TableAccessHandler


class TimestreamAccessHandler(TableAccessHandler):
    config_model = TimestreamTableAccessConfig
    resource_type = "aws_timestreamwrite_database"
    database_name_attribute = "database_name"
    read_actions = ["timestream:Select", "timestream:DescribeTable"]
    write_actions = ["timestream:WriteRecords", "timestream:DescribeTable"]

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="The selected LiveAnalytics table must be provisioned separately in this database. Application code uses the exported Region/database/table metadata with the Timestream SDK, which discovers service endpoints. DescribeEndpoints requires Resource '*'; record access remains table-scoped. Network reachability and external encryption-key policies remain separate. Queries spanning other tables require connections for those tables. No credentials are generated.",
            )
        ]

    def supporting_permissions(
        self, connection: ConnectionIR, resource: str
    ) -> ConnectionContribution:
        return ConnectionContribution(
            iam=[
                self._grant(
                    connection.source_name,
                    IAMStatement(
                        actions=["timestream:DescribeEndpoints"], resources=["*"]
                    ),
                )
            ]
        )
