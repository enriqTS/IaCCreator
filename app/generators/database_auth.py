"""Supported relational engines and Terraform IAM authentication guards."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models import ServiceType

IAM_DATABASE_ENGINES = {
    ServiceType.RDS: ("mysql", "mariadb", "postgres"),
    ServiceType.AURORA: ("aurora-mysql", "aurora-postgresql"),
}


def iam_database_expressions(service: ServiceType, name: str) -> dict[str, str]:
    is_cluster = service == ServiceType.AURORA
    resource = f"{'aws_rds_cluster' if is_cluster else 'aws_db_instance'}.{name}"
    resource_id = "cluster_resource_id" if is_cluster else "resource_id"
    arn = f"{resource}.arn"
    return {
        "host": f"{resource}.{'endpoint' if is_cluster else 'address'}",
        "port": f"tostring({resource}.port)",
        "region": f'split(":", {arn})[3]',
        "iam_resource_arn": f'format("arn:%s:rds-db:%s:%s:dbuser:%s", split(":", {arn})[1], split(":", {arn})[3], split(":", {arn})[4], {resource}.{resource_id})',
    }


def iam_database_attributes(service: ServiceType) -> dict:
    engines = HCLRenderer().render_expression(list(IAM_DATABASE_ENGINES[service]))
    return {
        "iam_database_authentication_enabled": True,
        "lifecycle": {
            "precondition": {
                "condition": Expr(f"contains({engines}, var.engine)"),
                "error_message": "IAM database connections require a supported MySQL, MariaDB, or PostgreSQL engine.",
            }
        },
    }
