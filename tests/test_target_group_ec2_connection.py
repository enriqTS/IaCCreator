"""EC2 target-group attachment coverage."""

from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture


def _project(target_type="instance", connection_config=None):
    spec = resolve_spec(ServiceType.TARGET_GROUP, ServiceType.EC2, "attaches", {})
    assert spec is not None
    payload = connection_architecture(spec)
    payload["resources"][0]["config"]["target_type"] = target_type
    payload["connections"][0]["connection_config"] = connection_config or {}
    return spec, IRBuilder().build(ArchitectureDescription.model_validate(payload))


def test_ec2_attachment_is_owned_by_target_group_module():
    _, project = _project(connection_config={"port": 8080})
    tree = CodeGenerator().generate(project)

    path = (
        "connection-check/modules/networking/target-group/source-resource/"
        "attachment_target_resource.tf"
    )
    attachment = tree[path]
    environment = tree["connection-check/environments/dev/main.tf"]

    assert 'resource "aws_lb_target_group_attachment"' in attachment
    assert "target_group_arn = aws_lb_target_group.source-resource.arn" in attachment
    assert "target_id = var.target_resource_instance_id" in attachment
    assert "port = 8080" in attachment
    assert (
        "target_resource_instance_id = module.target-resource.instance_id"
        in environment
    )


def test_ec2_attachment_reports_incompatible_target_type():
    spec, project = _project(target_type="ip")
    issues = spec.handler.validate(project.connections[0], project)

    assert len(issues) == 1
    assert issues[0].severity == "error"
    assert "instance target group" in issues[0].message
