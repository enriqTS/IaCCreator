"""OpenSearch service generator — produces HCL for aws_opensearch_domain resources."""

from app.generators.base import get_typed_config  # noqa: F401
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.opensearch_config import OpenSearchConfig
from app.models.ir_models import ResourceInstanceIR


def _resolve_config(instance: ResourceInstanceIR) -> OpenSearchConfig:
    """Resolve typed OpenSearchConfig, falling back to instance.config during migration."""
    if isinstance(instance.config, OpenSearchConfig):
        return instance.config
    return instance.config  # type: ignore[return-value]


class OpenSearchGenerator:
    """Generates Terraform files for OpenSearch domains."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_opensearch_domain resource."""
        config = _resolve_config(instance)
        attrs: dict = {"domain_name": Expr("var.domain_name")}
        if config._index_client_access:
            attrs["advanced_options"] = Expr(
                self._r.render_expression(
                    {"rest.action.multi.allow_explicit_index": "false"}
                )
            )
            attrs["domain_endpoint_options"] = {
                "enforce_https": True,
                "tls_security_policy": "Policy-Min-TLS-1-2-2019-07",
            }

        return self._r.render_resource("aws_opensearch_domain", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an OpenSearch domain."""
        parts = [
            self._r.render_variable(
                "domain_name", "string", "Name of the OpenSearch domain"
            ),
        ]
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an OpenSearch domain."""
        parts = [
            self._r.render_output(
                "domain_arn",
                f"aws_opensearch_domain.{instance.name}.arn",
                "ARN of the OpenSearch domain",
            ),
            self._r.render_output(
                "domain_endpoint",
                f"aws_opensearch_domain.{instance.name}.endpoint",
                "Endpoint of the OpenSearch domain",
            ),
        ]
        return "\n".join(parts)
