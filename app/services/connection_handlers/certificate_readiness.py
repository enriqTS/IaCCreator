"""Share certificate issuance waiting across managed certificate consumers."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.ir_models import (
    ConnectionContribution,
    ModuleOutput,
    ModuleResource,
    ProjectIR,
)
from app.services.connection_handlers.private_certificate_bindings import (
    resolve_private_certificate_binding,
)


def issued_certificate(
    name: str, project: ProjectIR, renderer: HCLRenderer
) -> tuple[str, ConnectionContribution]:
    certificate = f"aws_acm_certificate.{name}"
    ready = f"{certificate}.arn"
    result = ConnectionContribution()
    if resolve_private_certificate_binding(name, project) is None:
        resource = f"{name}_issuance"
        ready = f"aws_acm_certificate_validation.{resource}.certificate_arn"
        result.resources.append(
            ModuleResource(
                module=name,
                filename="certificate_issuance.tf",
                content=renderer.render_resource(
                    "aws_acm_certificate_validation",
                    resource,
                    {"certificate_arn": Expr(f"{certificate}.arn")},
                ),
            )
        )
    result.outputs.append(
        ModuleOutput(
            module=name,
            name="issued_certificate_arn",
            value=ready,
            description="Issued certificate ready for connected AWS services",
        )
    )
    return ready, result
