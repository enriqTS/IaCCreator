"""ACM certificate connection coverage."""

from app.models.input_models import ArchitectureDescription, ServiceType
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture


def test_cloudfront_uses_managed_viewer_certificate():
    spec = resolve_spec(
        ServiceType.CERTIFICATE_MANAGER, ServiceType.CLOUDFRONT, "secures", {}
    )
    assert spec is not None
    tree = CodeGenerator().generate(
        IRBuilder().build(
            ArchitectureDescription.model_validate(connection_architecture(spec))
        )
    )
    distribution = tree[
        "connection-check/modules/networking/cloudfront/target-resource/cloudfront.tf"
    ]
    environment = tree["connection-check/environments/dev/main.tf"]
    assert "acm_certificate_arn = var.certificate_arn" in distribution
    assert 'ssl_support_method = "sni-only"' in distribution
    assert "certificate_arn = module.source-resource.certificate_arn" in environment


def test_https_listener_uses_connected_certificate():
    payload = connection_architecture(
        resolve_spec(
            ServiceType.LOAD_BALANCER, ServiceType.TARGET_GROUP, "forwards_to", {}
        )
    )
    payload["resources"].append(
        {
            "id": "cert",
            "name": "certificate",
            "service_type": "certificate-manager",
            "config": {"domain_name": "example.com"},
            "terraform_variables": {},
        }
    )
    payload["connections"][0]["connection_config"] = {"port": 443, "protocol": "HTTPS"}
    payload["connections"].append(
        {
            "source": "certificate",
            "target": "source-resource",
            "source_id": "cert",
            "target_id": "src",
            "connection_type": "secures",
            "connection_config": {},
        }
    )
    project = IRBuilder().build(ArchitectureDescription.model_validate(payload))
    tree = CodeGenerator().generate(project)
    listener = tree[
        "connection-check/modules/networking/load-balancer/source-resource/listener_target_resource.tf"
    ]
    assert "certificate_arn = var.certificate_certificate_arn" in listener
    assert not resolve_spec(
        ServiceType.LOAD_BALANCER, ServiceType.TARGET_GROUP, "forwards_to", {}
    ).handler.validate(project.connections[0], project)
