"""API-owned custom domains using shared issued-certificate references."""

from app.generators.api_gateway.certificate_domain import (
    render_certificate_domain,
    render_certificate_mapping,
)
from app.models.connection_configs.api_gateway_certificate import (
    ApiGatewayCertificateConfig,
)
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ModuleOutput,
    ProjectIR,
)
from app.services.connection_handlers.api_gateway_certificate_bindings import (
    resolve_api_gateway_domains,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.certificate_readiness import issued_certificate
from app.services.connection_handlers.private_certificate_bindings import (
    resolve_private_certificate_binding,
)


class ApiGatewayCertificateHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        bindings = resolve_api_gateway_domains(connection.target_name, project)
        peers = [
            item
            for item in project.connections
            if item.target_name == connection.target_name
            and item.source_service == ServiceType.CERTIFICATE_MANAGER
            and item.connection_type == "secures"
        ]
        if connection is not peers[0]:
            return ConnectionContribution()
        config = self._find_instance(connection.target_name, project).config
        if config.stages is None:
            config.stages = []
        result = ConnectionContribution()
        certificates = {binding.certificate_name: binding for binding in bindings}
        for name, binding in sorted(certificates.items()):
            _, issuance = issued_certificate(name, project, self._renderer)
            result.merge(issuance)
            result.inputs.extend(
                [
                    ModuleInput(
                        module=connection.target_name,
                        name=binding.certificate_input,
                        value=f"module.{name}.issued_certificate_arn",
                    ),
                    ModuleInput(
                        module=connection.target_name,
                        name=binding.certificate_names_input,
                        value=f"module.{name}.api_gateway_certificate_names",
                        type="list(string)",
                    ),
                ]
            )
            ref = f"aws_acm_certificate.{name}"
            result.outputs.append(
                self._output(
                    name,
                    "api_gateway_certificate_names",
                    f"concat([{ref}.domain_name], tolist({ref}.subject_alternative_names))",
                    "Native certificate hostnames for coverage validation",
                )
            )
        domains = {binding.domain_name: binding for binding in bindings}
        content = [
            'data "aws_region" "api_custom_domains" {}',
            'data "aws_caller_identity" "api_custom_domains" {}',
        ]
        for hostname, binding in sorted(domains.items()):
            content.append(render_certificate_domain(binding, config, self._renderer))
            ref = f"aws_apigatewayv2_domain_name.{binding.domain_resource}"
            for suffix, expression in (
                ("name", f"{ref}.domain_name"),
                ("arn", f"{ref}.arn"),
                (
                    "target_domain_name",
                    f"{ref}.domain_name_configuration[0].target_domain_name",
                ),
                (
                    "hosted_zone_id",
                    f"{ref}.domain_name_configuration[0].hosted_zone_id",
                ),
            ):
                result.outputs.append(
                    ModuleOutput(
                        module=connection.target_name,
                        name=f"{binding.domain_resource}_{suffix}",
                        value=expression,
                        description=f"Custom domain {hostname} {suffix}",
                    )
                )
        content.extend(
            render_certificate_mapping(binding, self._renderer) for binding in bindings
        )
        result.resources.append(
            self._resource(
                connection.target_name, "certificate_domains.tf", "\n".join(content)
            )
        )
        return result

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        bindings = resolve_api_gateway_domains(connection.target_name, project)
        config = self._find_instance(connection.target_name, project).config
        request = ApiGatewayCertificateConfig.model_validate(
            connection.connection_config
        )
        binding = next(
            item
            for item in bindings
            if item.domain_name == request.domain_name
            and item.api_mapping_key == request.api_mapping_key
        )
        issues = [
            ConnectionIssue(
                severity="warning",
                message="Configure DNS to point this hostname to the exported target domain or Route 53 alias target. This connection creates the domain and API mappings; application routes and integrations remain required.",
            )
        ]
        if resolve_private_certificate_binding(connection.source_name, project) is None:
            issues.append(
                ConnectionIssue(
                    severity="warning",
                    message="Complete public ACM DNS or email validation before the shared issuance waiter can create the custom domain.",
                )
            )
        else:
            issues.append(
                ConnectionIssue(
                    severity="warning",
                    message="Clients must trust the issuing private CA root to call this TLS endpoint.",
                )
            )
        stage = next(
            (
                item
                for item in config.stages or []
                if item.get("name", "$default") == binding.stage_name
            ),
            {"auto_deploy": True},
        )
        if not stage.get("auto_deploy", False):
            issues.append(
                ConnectionIssue(
                    severity="warning",
                    message="Deploy API changes to the selected stage separately; this connection does not create API deployments.",
                )
            )
        if config.mutual_tls_truststore_uri and not config.disable_execute_api_endpoint:
            issues.append(
                ConnectionIssue(
                    severity="warning",
                    message="Disable the default execute-api endpoint if clients must authenticate through the custom domain's mutual TLS truststore.",
                )
            )
        return issues
