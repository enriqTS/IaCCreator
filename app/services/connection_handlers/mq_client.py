"""MQ endpoint bindings preserve every broker instance for client-managed failover."""

from app.generators.hcl_renderer import Expr
from app.models.connection_configs.mq import MQ_PROTOCOL_SCHEMES, MqClientConfig
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class MqClientHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Exports ActiveMQ TLS endpoints for application configuration. Broker users, queue/topic permissions, credential delivery, and network reachability must be configured separately. Existing Secrets Manager connections can supply credentials; this connection does not read the broker's administrator password or grant IAM messaging permissions. For active/standby brokers, configure the client's failover/reconnection support with all exported endpoints; list order does not identify the active broker. Endpoint URI syntax may need adaptation for your client library. No Lambda event-source mapping is created.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        config = MqClientConfig.model_validate(connection.connection_config)
        source, target = connection.source_name, connection.target_name
        output = f"client_{config.protocol}_endpoints"
        variable = f"mq_{target}_{config.protocol}_endpoints"
        scheme = MQ_PROTOCOL_SCHEMES[config.protocol]
        expression = (
            f"sort(distinct(flatten([for broker in aws_mq_broker.{target}.instances : "
            f'[for endpoint in broker.endpoints : endpoint if split("://", endpoint)[0] == "{scheme}"]])))'
        )
        result = ConnectionContribution(
            outputs=[
                self._output(
                    target,
                    output,
                    expression,
                    "ActiveMQ TLS endpoints for every broker instance",
                )
            ],
            inputs=[
                ModuleInput(
                    module=source,
                    name=variable,
                    value=f"module.{target}.{output}",
                    type="list(string)",
                )
            ],
        )
        result.outputs.append(
            self._output(
                source,
                f"mq_{target}_{config.protocol}_client",
                self._renderer.render_expression(
                    {
                        "engine": "ActiveMQ",
                        "protocol": config.protocol,
                        "endpoints": Expr(f"var.{variable}"),
                        "tls": True,
                    }
                ),
                "ActiveMQ client metadata; credentials and broker permissions remain separate",
            )
        )
        return result
