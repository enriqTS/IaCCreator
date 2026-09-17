"""Generate TLS-enabled serverless caches without provisioning credentials."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.elasticache_serverless_config import (
    ElastiCacheServerlessConfig,
)
from app.models.ir_models import ResourceInstanceIR


class ElastiCacheServerlessGenerator:
    def __init__(self):
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, ElastiCacheServerlessConfig)
        attrs = {
            "name": Expr("var.cache_name"),
            "engine": Expr("var.engine"),
            "subnet_ids": Expr("var.subnet_ids"),
            "security_group_ids": Expr("var.security_group_ids"),
        }
        if config.user_group_id is not None:
            attrs["user_group_id"] = Expr("var.user_group_id")
        if config._iam_client_access:
            attrs["lifecycle"] = {
                "precondition": {
                    "condition": Expr(
                        'contains(["valkey", "redis"], var.engine) && try(length(trimspace(var.user_group_id)) > 0, false)'
                    ),
                    "error_message": "Serverless IAM clients require Valkey/Redis and an existing user group containing the IAM user.",
                },
                "postcondition": {
                    "condition": Expr(
                        'try(tonumber(split(".", self.full_engine_version)[0]) > 7 || (tonumber(split(".", self.full_engine_version)[0]) == 7 && (self.engine == "redis" || tonumber(split(".", self.full_engine_version)[1]) >= 2)), false)'
                    ),
                    "error_message": "Serverless IAM clients require Redis 7.0+ or Valkey 7.2+.",
                },
            }
        return self._r.render_resource(
            "aws_elasticache_serverless_cache", instance.name, attrs
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, ElastiCacheServerlessConfig)
        fields = [
            ("cache_name", "string", "Serverless cache name"),
            ("engine", "string", "Valkey or Redis engine"),
            ("subnet_ids", "list(string)", "VPC subnet IDs"),
            ("security_group_ids", "list(string)", "VPC security group IDs"),
        ]
        if config.user_group_id is not None:
            fields.append(("user_group_id", "string", "Existing cache user group"))
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_elasticache_serverless_cache.{instance.name}"
        return "\n".join(
            self._r.render_output(field, f"{ref}.{field}", f"Serverless cache {field}")
            for field in ("arn", "endpoint", "reader_endpoint")
        )
