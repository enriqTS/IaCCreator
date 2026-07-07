"""CodeCommit-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class CodeCommitConfig(BaseServiceConfig):
    """CodeCommit-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.CODECOMMIT] = ServiceType.CODECOMMIT

    _schema_field_order: ClassVar[tuple[str, ...]] = ("repository_name",)

    # ── General ───────────────────────────────────────────────────────────
    repository_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the CodeCommit repository",
    )
