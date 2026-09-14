"""Supported relational engines and Terraform IAM authentication guards."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models import ServiceType

IAM_DATABASE_ENGINES = {
    ServiceType.RDS: ("mysql", "mariadb", "postgres"),
    ServiceType.AURORA: ("aurora-mysql", "aurora-postgresql"),
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
