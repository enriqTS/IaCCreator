import json

import yaml


def validate_package_buildspec(content: str) -> None:
    try:
        document = yaml.safe_load(content)
        json.dumps(document, allow_nan=False)
    except (ValueError, TypeError, RecursionError, yaml.YAMLError) as exc:
        raise ValueError(
            "Package login requires a finite JSON-compatible inline YAML buildspec"
        ) from exc
    if not isinstance(document, dict) or str(document.get("version")) != "0.2":
        raise ValueError(
            "Package login requires an inline version 0.2 buildspec; file paths are unsupported"
        )
    phases = document.get("phases", {})
    if not isinstance(phases, dict):
        raise ValueError("Inline buildspec phases must be an object")
    pre_build = phases.get("pre_build", {})
    if not isinstance(pre_build, dict):
        raise ValueError("Inline pre_build must be an object")
    commands = pre_build.get("commands", [])
    if not isinstance(commands, list) or any(
        not isinstance(command, str) for command in commands
    ):
        raise ValueError("Inline pre_build commands must be a list of strings")
