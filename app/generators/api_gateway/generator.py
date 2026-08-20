"""API Gateway generator — composes the per-concern sub-generators."""

from app.generators.api_gateway import (
    api,
    api_keys,
    authorizers,
    domain,
    integrations,
    outputs,
    routes,
    stages,
    vpc_links,
)
from app.generators.api_gateway._support import resolve_config
from app.generators.api_gateway_validator import APIGatewayValidator
from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class APIGatewayGenerator:
    """Generates Terraform files for API Gateway (HTTP and WebSocket) resources."""

    def __init__(self) -> None:
        self._r = HCLRenderer()
        self._validator = APIGatewayValidator()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Validate the instance, then render every applicable sub-resource."""
        errors = self._validator.validate(instance)
        if errors:
            error_messages = [f"[{e.code}] {e.field}: {e.message}" for e in errors]
            raise ValueError(
                f"API Gateway validation failed with {len(errors)} error(s):\n"
                + "\n".join(error_messages)
            )

        config = resolve_config(instance)
        parts = [
            api.render_api_resource(instance, config, self._r),
            api_keys.render_api_keys(instance, config, self._r),
        ]

        # Each block is emitted only when its config section is present, so a config
        # using just the original fields still produces only the API resource.
        optional = [
            ("routes", routes.render_routes),
            ("stages", stages.render_stages),
            ("authorizers", authorizers.render_authorizers),
            ("custom_domain", domain.render_domain),
            ("vpc_links", vpc_links.render_vpc_links),
            ("integrations", integrations.render_integrations),
        ]
        for field, render in optional:
            if field == "routes":
                if (
                    getattr(config, "routes", None) is None
                    and not config.api_key_required
                ):
                    continue
            elif getattr(config, field, None) is None:
                continue
            parts.append(render(instance, config, self._r))

        return "\n".join(p for p in parts if p)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Every concern contributes the variables its resources reference."""
        config = resolve_config(instance)
        parts: list[str] = []
        for module in (api, routes, stages, authorizers, domain, integrations):
            parts.extend(module.render_variables(config, self._r))
        parts.extend(api.render_metadata_variables(config, self._r))
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an API Gateway instance."""
        return outputs.render_outputs(instance, resolve_config(instance), self._r)
