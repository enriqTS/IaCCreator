from pydantic import StrictInt, StrictStr, field_validator

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule

REVISION_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,255}$"


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
        if (
            any(token in value for token in ("..", "//"))
            or value.endswith((".", "/"))
            or any(
                part.startswith(".") or part.endswith(".lock")
                for part in value.split("/")
            )
        ):
            raise ValueError(
                "Select a literal Git branch, tag, or commit without invalid ref components"
            )
        return value
