"""App Runner-specific configuration model."""

from typing import ClassVar, Literal

from pydantic import PrivateAttr

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class AppRunnerConfig(BaseServiceConfig):
    """App Runner-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.APP_RUNNER] = ServiceType.APP_RUNNER

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "service_name",
        "image_identifier",
        "image_repository_type",
        "access_role_arn",
        "instance_role_arn",
        "runtime_environment_secrets",
    )

    # ── General ───────────────────────────────────────────────────────────
    service_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the App Runner service",
    )
    image_identifier: str | None = TerraformField(
        None,
        group="General",
        description="Container image identifier for the App Runner service",
    )

    image_repository_type: Literal["ECR", "ECR_PUBLIC"] = TerraformField(
        "ECR", group="Source", description="Container image repository type"
    )
    access_role_arn: str | None = TerraformField(
        None,
        group="Source",
        description="ECR image-pull role trusted by build.apprunner.amazonaws.com",
    )
    instance_role_arn: str | None = TerraformField(
        None,
        group="Runtime",
        description="Runtime role trusted by tasks.apprunner.amazonaws.com",
    )
    runtime_environment_secrets: dict[str, str] = TerraformField(
        {},
        group="Runtime",
        description="External secret or parameter ARNs by environment variable name",
    )
    _inject_runtime_secrets: bool = PrivateAttr(default=False)

    # ── Internal (not Terraform variables) ────────────────────────────────
    apprunner_source_type: str | None = None
