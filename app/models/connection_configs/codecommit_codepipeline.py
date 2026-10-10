from pydantic import StrictStr, field_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.git_reference import GIT_REFERENCE_PATTERN, validate_git_reference
from app.models.input_models._metadata import ValidationRule


class CodeCommitPipelineConfig(BaseConnectionConfig):
    stage_name: StrictStr = ConnectionField(
        "Source",
        label="Source stage",
        description="Existing first stage containing the CodeCommit source action",
        validation=ValidationRule(pattern=r"^[A-Za-z0-9.@_-]{1,100}$"),
    )
    action_name: StrictStr = ConnectionField(
        "Source",
        label="Source action",
        description="Existing AWS CodeCommit action; its output artifact is preserved",
        validation=ValidationRule(pattern=r"^[A-Za-z0-9.@_-]{1,100}$"),
    )
    branch_name: StrictStr = ConnectionField(
        "main",
        label="Branch",
        description="Existing repository branch; polling is disabled and ZIP output is used",
        validation=ValidationRule(pattern=GIT_REFERENCE_PATTERN),
    )

    @field_validator("branch_name")
    @classmethod
    def valid_branch(cls, value: str) -> str:
        return validate_git_reference(value)
