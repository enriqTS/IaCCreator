"""Resolve policy-template references without leaking resources across modules."""

import re

from app.generators.hcl_renderer import Expr
from app.models.ir_models import (
    ConnectionContribution,
    ModuleInput,
    ModuleOutput,
    ResourceInstanceIR,
)

_REFERENCE = re.compile(r"\$\{((?:var|data|aws_[a-z0-9_]+)\.[A-Za-z0-9_.-]+)\}")


def policy_references(instance: ResourceInstanceIR) -> list[str]:
    return sorted(
        {
            match
            for statement in instance.iam_statements
            for resource in statement.resources
            for match in _REFERENCE.findall(resource)
        }
    )


def input_name(reference: str) -> str:
    return "iam_" + reference.replace(".", "_").replace("-", "_")


def cross_module_inputs(instance: ResourceInstanceIR) -> ConnectionContribution:
    result = ConnectionContribution()
    for reference in policy_references(instance):
        parts = reference.split(".")
        if (
            len(parts) != 3
            or not parts[0].startswith("aws_")
            or parts[1] == instance.name
        ):
            continue
        kind, owner, attribute = parts
        output = f"iam_{kind}_{attribute}"
        result.outputs.append(
            ModuleOutput(
                module=owner,
                name=output,
                value=reference,
                description="Resource identity used by an execution policy",
            )
        )
        result.inputs.append(
            ModuleInput(
                module=instance.name,
                name=input_name(reference),
                value=f"module.{owner}.{output}",
                description="Resource identity used by an execution policy",
            )
        )
    return result


def template_context(instance: ResourceInstanceIR) -> dict:
    context: dict = {}
    for reference in policy_references(instance):
        parts = reference.split(".")
        value = reference
        if (
            len(parts) == 3
            and parts[0].startswith("aws_")
            and parts[1] != instance.name
        ):
            value = "var." + input_name(reference)
        node = context
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = Expr(value)
    return context
