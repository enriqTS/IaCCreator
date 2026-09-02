"""Load-balancer listener connection coverage."""

from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture


def _project(config=None):
    spec = resolve_spec(
        ServiceType.LOAD_BALANCER, ServiceType.TARGET_GROUP, "forwards_to", {}
    )
    assert spec is not None
    payload = connection_architecture(spec)
    payload["connections"][0]["connection_config"] = config or {}
    return spec, IRBuilder().build(ArchitectureDescription.model_validate(payload))


def test_listener_forwards_to_managed_target_group():
    _, project = _project({"port": 8080, "protocol": "HTTP"})
    tree = CodeGenerator().generate(project)

    listener = tree[
        "connection-check/modules/networking/load-balancer/source-resource/"
        "listener_target_resource.tf"
    ]
    environment = tree["connection-check/environments/dev/main.tf"]

    assert 'resource "aws_lb_listener"' in listener
    assert "load_balancer_arn = aws_lb.source-resource.arn" in listener
    assert "port = 8080" in listener
    assert 'protocol = "HTTP"' in listener
    assert "target_group_arn = var.target_resource_target_group_arn" in listener
    assert (
        "target_resource_target_group_arn = module.target-resource.target_group_arn"
        in environment
    )


def test_secure_listener_reports_missing_certificate_connection():
    spec, project = _project({"port": 443, "protocol": "HTTPS"})
    issues = spec.handler.validate(project.connections[0], project)

    assert len(issues) == 1
    assert issues[0].severity == "error"
    assert "certificate connection" in issues[0].message
