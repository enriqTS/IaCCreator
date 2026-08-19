"""Derives the arguments an environment must pass to an instance module."""

from __future__ import annotations

import re
from typing import Any

from app.models.ir_models import ResourceInstanceIR

_VARIABLE_BLOCK = re.compile(r'^variable "([^"]+)" \{$')


def required_variable_names(variables_tf: str) -> list[str]:
    """Return variables declared without a default, which the caller must supply."""
    names: list[str] = []
    current: str | None = None
    has_default = False

    for line in variables_tf.split("\n"):
        match = _VARIABLE_BLOCK.match(line)
        if match:
            current = match.group(1)
            has_default = False
            continue
        if current is None:
            continue
        if line.startswith("  default"):
            has_default = True
        elif line == "}":
            if not has_default:
                names.append(current)
            current = None

    return names


def module_arguments(instance: ResourceInstanceIR, variables_tf: str) -> dict[str, Any]:
    """Map each defaultless module variable to its value from the instance config."""
    arguments: dict[str, Any] = {}
    for name in required_variable_names(variables_tf):
        value = getattr(instance.config, name, None)
        if value is None:
            value = instance.terraform_variables.get(name)
        if value is not None:
            arguments[name] = value
    return arguments
