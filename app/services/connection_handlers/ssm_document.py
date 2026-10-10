"""Association documents require executable schema 2.2 content and declared parameters."""

import json
import re

import yaml

from app.models.connection_configs.ssm_ec2 import (
    DOCUMENT_NAME_PATTERN,
    PARAMETER_NAME_PATTERN,
)
from app.models.input_models.systems_manager_config import SystemsManagerConfig


def command_parameters(config: SystemsManagerConfig) -> dict[str, dict]:
    if config.document_type != "Command":
        raise ValueError("EC2 associations require a Command document")
    if not re.fullmatch(DOCUMENT_NAME_PATTERN, config.document_name):
        raise ValueError("Associations require a bounded local document name")
    if config.document_format not in {"JSON", "YAML"}:
        raise ValueError("Command associations require JSON or YAML content")
    if len(config.content.encode("utf-8")) > 65536:
        raise ValueError("Command content must not exceed 64 KiB")
    try:
        if config.document_format == "YAML" and any(
            isinstance(token, yaml.tokens.AliasToken)
            for token in yaml.scan(config.content)
        ):
            raise ValueError("YAML aliases are unsupported in association documents")
        document = (
            json.loads(config.content)
            if config.document_format == "JSON"
            else yaml.safe_load(config.content)
        )
        json.dumps(document, allow_nan=False)
    except (ValueError, TypeError, RecursionError, yaml.YAMLError) as exc:
        raise ValueError(
            "Command content must be a finite JSON or YAML object"
        ) from exc
    if not isinstance(document, dict) or str(document.get("schemaVersion")) != "2.2":
        raise ValueError("Command associations require document schema 2.2")
    steps = document.get("mainSteps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("Command documents require at least one main step")
    names = set()
    for step in steps:
        if (
            not isinstance(step, dict)
            or not isinstance(step.get("name"), str)
            or not re.fullmatch(r"[A-Za-z0-9_]{1,128}", step["name"])
            or step["name"] in names
            or not isinstance(step.get("action"), str)
            or not step["action"].startswith("aws:")
            or not isinstance(step.get("inputs"), dict)
        ):
            raise ValueError(
                "Command steps require unique names, AWS actions, and input objects"
            )
        names.add(step["name"])
    parameters = document.get("parameters", {})
    if not isinstance(parameters, dict):
        raise ValueError("Document parameters must be an object")
    for name, parameter in parameters.items():
        if (
            not isinstance(name, str)
            or not re.fullmatch(PARAMETER_NAME_PATTERN, name)
            or not isinstance(parameter, dict)
            or parameter.get("type") not in ("String", "StringList")
        ):
            raise ValueError(
                "Command parameters require named String or StringList declarations"
            )
        if "default" in parameter:
            default = parameter["default"]
            if parameter["type"] == "String" and not isinstance(default, str):
                raise ValueError("String parameter defaults must be strings")
            if parameter["type"] == "StringList" and (
                not isinstance(default, list)
                or any(not isinstance(v, str) for v in default)
            ):
                raise ValueError("StringList defaults must be lists of strings")
    return parameters
