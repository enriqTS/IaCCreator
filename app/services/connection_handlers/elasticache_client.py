"""Standalone cache clients receive native endpoints without IAM login claims."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class ElastiCacheClientHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Exports endpoint metadata for Memcached or standalone Redis. The existing cluster generator does not enable TLS or configure authentication; inspect the exported TLS setting and secure network access separately. No IAM data-access permissions or credentials are created. Memcached clients must distribute keys across nodes or use the configuration endpoint with an Auto Discovery-capable client. Static node lists must be refreshed after scaling. Valkey, Redis replication groups, serverless caches, IAM login, and failover are outside this connection.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        cluster = self._find_instance(connection.target_name, project)
        config = cluster.config
        if (
            config.engine not in {"redis", "memcached"}
            or config.num_cache_nodes is None
            or not 1 <= config.num_cache_nodes <= 40
            or (config.engine == "redis" and config.num_cache_nodes != 1)
            or not config.node_type
            or not config.parameter_group_name
        ):
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("elasticache",),
                        "msg": "Select redis with one node or memcached with 1–40 nodes, a node type, and a compatible parameter group",
                    }
                ],
            )
        config._client_access = True
        source, target = connection.source_name, connection.target_name
        ref = f"aws_elasticache_cluster.{target}"
        fields = {
            "engine": (f"{ref}.engine", "string"),
            "nodes": (
                f"[for id, node in {{ for node in {ref}.cache_nodes : node.id => node }} : {{ address = node.address, port = node.port }}]",
                "list(object({ address = string, port = number }))",
            ),
            "tls": (f"coalesce({ref}.transit_encryption_enabled, false)", "bool"),
            "configuration_endpoint": (
                f'{ref}.engine == "memcached" ? {ref}.configuration_endpoint : ""',
                "string",
            ),
        }
        result = ConnectionContribution()
        metadata = {}
        for field, (expression, kind) in fields.items():
            output, variable = f"client_{field}", f"elasticache_{target}_{field}"
            result.outputs.append(self._output(target, output, expression))
            result.inputs.append(
                ModuleInput(
                    module=source,
                    name=variable,
                    value=f"module.{target}.{output}",
                    type=kind,
                )
            )
            metadata[field] = Expr(f"var.{variable}")
        result.outputs.append(
            self._output(
                source,
                f"elasticache_{target}_client",
                self._renderer.render_expression(metadata),
                "Standalone cache client metadata; access control and networking remain separate",
            )
        )
        return result
