"""Aurora service generator — produces HCL for aws_rds_cluster resources."""

from app.generators.database_auth import iam_database_attributes
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.aurora_config import AuroraConfig
from app.models.ir_models import ResourceInstanceIR


def _resolve_config(instance: ResourceInstanceIR) -> AuroraConfig:
    """Resolve typed AuroraConfig from the instance."""
    if isinstance(instance.config, AuroraConfig):
        return instance.config
    return instance.config  # type: ignore[return-value]


class AuroraGenerator:
    """Generates Terraform files for Aurora (RDS) clusters."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_rds_cluster resource."""
        config = _resolve_config(instance)
        attrs: dict = {"cluster_identifier": Expr("var.cluster_identifier")}
        if config._iam_database_access:
            attrs.update(iam_database_attributes(instance.service_type))
        if config._appsync_data_api:
            attrs.update(
                {
                    "engine_mode": "provisioned",
                    "enable_http_endpoint": True,
                    "storage_encrypted": True,
                    "manage_master_user_password": True,
                    "serverlessv2_scaling_configuration": {
                        "min_capacity": 0.5,
                        "max_capacity": 2.0,
                    },
                    "database_name": Expr("var.database_name"),
                    "master_username": Expr("var.master_username"),
                }
            )
        elif config.manage_master_user_password:
            attrs["manage_master_user_password"] = Expr(
                "var.manage_master_user_password"
            )
        if config.engine is not None:
            attrs["engine"] = Expr("var.engine")
        if config.engine_version is not None:
            attrs["engine_version"] = Expr("var.engine_version")
        if config.master_username is not None and not config._appsync_data_api:
            attrs["master_username"] = Expr("var.master_username")
        cluster = self._r.render_resource("aws_rds_cluster", instance.name, attrs)
        if not config._appsync_data_api:
            return cluster
        writer = self._r.render_resource(
            "aws_rds_cluster_instance",
            f"{instance.name}_writer",
            {
                "identifier": f"{instance.name}-writer",
                "cluster_identifier": Expr(f"aws_rds_cluster.{instance.name}.id"),
                "instance_class": "db.serverless",
                "engine": Expr(f"aws_rds_cluster.{instance.name}.engine"),
                "publicly_accessible": False,
            },
        )
        return cluster + writer

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an Aurora cluster."""
        config = _resolve_config(instance)
        parts = [
            self._r.render_variable(
                "cluster_identifier", "string", "Identifier for the Aurora cluster"
            ),
        ]
        if config.engine is not None:
            parts.append(
                self._r.render_variable(
                    "engine",
                    "string",
                    "Database engine for the Aurora cluster",
                    default=config.engine,
                )
            )
        if config.engine_version is not None:
            parts.append(
                self._r.render_variable(
                    "engine_version",
                    "string",
                    "Aurora engine version",
                    default=config.engine_version,
                )
            )
        if config.database_name is not None:
            parts.append(
                self._r.render_variable(
                    "database_name", "string", "Initial logical database name"
                )
            )
        if config.master_username is not None or config._appsync_data_api:
            parts.append(
                self._r.render_variable(
                    "master_username",
                    "string",
                    "Master username for the Aurora cluster",
                    default=config.master_username or "dbadmin",
                )
            )
        if config.manage_master_user_password and not config._appsync_data_api:
            parts.append(
                self._r.render_variable(
                    "manage_master_user_password",
                    "bool",
                    "Manage master password in Secrets Manager",
                    default=True,
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an Aurora cluster."""
        parts = [
            self._r.render_output(
                "cluster_arn",
                f"aws_rds_cluster.{instance.name}.arn",
                "ARN of the Aurora cluster",
            ),
            self._r.render_output(
                "cluster_endpoint",
                f"aws_rds_cluster.{instance.name}.endpoint",
                "Endpoint of the Aurora cluster",
            ),
        ]
        if _resolve_config(instance)._appsync_data_api:
            parts.extend(
                [
                    self._r.render_output(
                        "data_api_cluster_arn",
                        f"aws_rds_cluster.{instance.name}.arn",
                        "Data API cluster ARN after the writer is ready",
                        depends_on=[f"aws_rds_cluster_instance.{instance.name}_writer"],
                    ),
                    self._r.render_output(
                        "database_name",
                        f"aws_rds_cluster.{instance.name}.database_name",
                        "Initial logical database name",
                    ),
                    self._r.render_output(
                        "master_secret_arn",
                        f"aws_rds_cluster.{instance.name}.master_user_secret[0].secret_arn",
                        "Administrator secret ARN for database bootstrap",
                    ),
                ]
            )
        return "\n".join(parts)
