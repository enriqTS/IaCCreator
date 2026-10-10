from pydantic import StrictInt, StrictStr, field_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.git_reference import (
    GIT_REFERENCE_PATTERN as REVISION_PATTERN,
)
from app.models.git_reference import (
    validate_git_reference,
)
from app.models.input_models._metadata import ValidationRule


class CodeCommitBuildConfig(BaseConnectionConfig):
    source_version: StrictStr = ConnectionField(
        "main",
        label="Branch, tag, or commit",
        description="Existing ASCII Git reference or commit ID; defaults to main",
        validation=ValidationRule(pattern=REVISION_PATTERN),
    )
    git_clone_depth: StrictInt = ConnectionField(
        1,
        label="Clone depth",
        type="number",
        description="Zero selects full history; otherwise fetch 1–25 commits",
        validation=ValidationRule(min=0, max=25),
    )

    @field_validator("source_version")
    @classmethod
    def valid_revision(cls, value: str) -> str:
        return validate_git_reference(value)
