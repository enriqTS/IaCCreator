"""Shared base models and common fields for all service configurations."""

from pydantic import BaseModel


class BaseServiceConfig(BaseModel):
    """Shared base for all service configs. Icon-only services use this directly."""
    tags: dict[str, str] | None = None
    description: str | None = None
    environment_variables: dict[str, str] | None = None
