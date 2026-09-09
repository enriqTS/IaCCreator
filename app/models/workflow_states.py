"""Validation of replaceable JSONPath workflow placeholders."""

import json

PASS_STATE_FIELDS = (
    "Type",
    "Next",
    "End",
    "Comment",
    "InputPath",
    "OutputPath",
    "ResultPath",
    "Result",
    "QueryLanguage",
)


def placeholder_errors(definition: str, names: set[str]) -> list[str]:
    try:
        workflow = json.loads(definition)
    except (TypeError, ValueError):
        return ["The workflow definition must be valid JSON"]
    if not isinstance(workflow, dict) or not isinstance(workflow.get("States"), dict):
        return ["The workflow definition must contain a States object"]
    states = workflow["States"]
    if (
        not isinstance(workflow.get("StartAt"), str)
        or workflow["StartAt"] not in states
    ):
        return ["StartAt must identify an existing state"]
    if workflow.get("QueryLanguage", "JSONPath") != "JSONPath":
        return ["Secret tasks currently support JSONPath workflows only"]
    errors = []
    for name in sorted(names):
        state = states.get(name)
        if not isinstance(state, dict) or state.get("Type") != "Pass":
            errors.append(f"{name!r} must identify an existing top-level Pass state")
            continue
        if state.get("QueryLanguage", "JSONPath") != "JSONPath":
            errors.append(f"{name!r} must use JSONPath")
        if set(state) - set(PASS_STATE_FIELDS):
            errors.append(f"{name!r} contains unsupported Pass-state fields")
        ends = state.get("End") is True and "Next" not in state
        follows = (
            "End" not in state
            and isinstance(state.get("Next"), str)
            and state["Next"] in states
        )
        if not (ends or follows):
            errors.append(
                f"{name!r} must have End=true or a Next reference to an existing state"
            )
    return errors
