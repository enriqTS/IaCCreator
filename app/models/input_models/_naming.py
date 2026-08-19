"""Naming rules for resources, shared by validation and the schema served to the editor."""

from __future__ import annotations

import re

# Names become Terraform resource labels, module names and directory names, so they must
# be valid HCL identifiers: a letter or underscore first, then letters, digits, _ or -.
RESOURCE_NAME_PATTERN = r"^[A-Za-z_][A-Za-z0-9_-]*$"

RESOURCE_NAME_DESCRIPTION = (
    "Must start with a letter or underscore and contain only letters, digits, "
    "underscores or hyphens"
)

RESOURCE_NAME_MAX_LENGTH = 64

_RESOURCE_NAME = re.compile(RESOURCE_NAME_PATTERN)


def is_valid_resource_name(name: str) -> bool:
    """Return whether a name is usable as a Terraform identifier and directory name."""
    return (
        bool(name)
        and len(name) <= RESOURCE_NAME_MAX_LENGTH
        and bool(_RESOURCE_NAME.match(name))
    )
