GIT_REFERENCE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,255}$"


def validate_git_reference(value: str) -> str:
    if (
        any(token in value for token in ("..", "//"))
        or value.endswith((".", "/"))
        or any(
            part.startswith(".") or part.endswith(".lock") for part in value.split("/")
        )
    ):
        raise ValueError(
            "Select a literal Git reference without invalid ref components"
        )
    return value
