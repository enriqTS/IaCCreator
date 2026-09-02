"""Lambda target-group attachment coverage."""

from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture


def _project(target_type="lambda"):
    spec = resolve_spec(ServiceType.TARGET_GROUP, ServiceType.LAMBDA, "attaches", {})
    assert spec is not None
    payload = connection_architecture(spec)
    payload["resources"][0]["config"]["target_type"] = target_type
    return spec, IRBuilder().build(ArchitectureDescription.model_validate(payload))


def test_lambda_attachment_and_permission_are_target_group_owned():
    _, project = _project()
    tree = CodeGenerator().generate(project)
    prefix = "connection-check/modules/networking/target-group/source-resource"

    attachment = tree[f"{prefix}/attachment_target_resource.tf"]
    permission = tree[f"{prefix}/permission_target_resource.tf"]
    environment = tree["connection-check/environments/dev/main.tf"]

    assert 'resource "aws_lb_target_group_attachment"' in attachment
    assert "target_id = var.target_resource_function_arn" in attachment
    assert "aws_lambda_permission.target_resource_permission" in attachment
    assert 'principal = "elasticloadbalancing.amazonaws.com"' in permission
    assert "source_arn = aws_lb_target_group.source-resource.arn" in permission
    assert (
        "target_resource_function_arn = module.target-resource.function_arn"
        in environment
    )
    assert (
        "target_resource_function_name = module.target-resource.function_name"
        in environment
    )


def test_lambda_attachment_reports_non_lambda_target_group():
    spec, project = _project(target_type="instance")
    issues = spec.handler.validate(project.connections[0], project)

    assert len(issues) == 1
    assert issues[0].severity == "error"
    assert "lambda target group" in issues[0].message
