"""KMS references for workflow roles that publish to generated SNS or SQS targets."""

from app.generators.hcl_renderer import Expr
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ModuleInput,
    ModuleOutput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.kms_references import KMS_INPUTS, managed_key


def workflow_message_keys(
    workflow: str,
    targets: list[str],
    service: ServiceType,
    project: ProjectIR,
) -> tuple[ConnectionContribution, list[Expr], str]:
    result = ConnectionContribution()
    references = []
    data_sources = []
    field = KMS_INPUTS[service]
    lookup = BaseConnectionHandler._find_instance
    for index, name in enumerate(targets):
        target = lookup(name, project)
        key = managed_key(name, project)
        external = getattr(target.config, field)
        if not key and not external:
            continue
        variable = f"workflow_{service.value}_key_{index}_arn"
        if key:
            result.inputs.append(
                ModuleInput(
                    module=workflow,
                    name=variable,
                    value=f"module.{key}.key_arn",
                )
            )
            references.append(Expr(f"var.{variable}"))
        else:
            result.outputs.append(
                ModuleOutput(
                    module=name, name="kms_access_key_id", value=f"var.{field}"
                )
            )
            result.inputs.append(
                ModuleInput(
                    module=workflow,
                    name=variable,
                    value=f"module.{name}.kms_access_key_id",
                )
            )
            data_sources.append(
                f'data "aws_kms_key" "{variable}" {{\n  key_id = var.{variable}\n}}\n'
            )
            references.append(Expr(f"data.aws_kms_key.{variable}.arn"))
    return result, references, "".join(data_sources)
