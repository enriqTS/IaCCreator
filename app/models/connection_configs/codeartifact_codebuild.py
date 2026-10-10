from typing import Literal

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import OptionEntry, ValidationRule

DOMAIN_PATTERN = r"^[a-z][a-z0-9-]{0,48}[a-z0-9]$"
REPOSITORY_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{1,99}$"


class CodeArtifactBuildConfig(BaseConnectionConfig):
    tool: Literal["npm", "pip"] = ConnectionField(
        "npm",
        label="Package manager",
        type="select",
        description="Log in before pre-build commands; package access is read-only",
        options=[
            OptionEntry(value="npm", label="npm"),
            OptionEntry(value="pip", label="pip"),
        ],
        validation=ValidationRule(allowed_values=["npm", "pip"]),
    )
