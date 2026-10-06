"""Own validation CNAMEs in hosted zones and share issuance waiters in ACM."""

from app.generators.certificate_dns import zone_dns_preconditions
from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.certificate_dns_bindings import (
    resolve_certificate_dns,
)
from app.services.connection_handlers.certificate_readiness import issued_certificate


class CertificateDnsHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        bindings = resolve_certificate_dns(project)
        result = ConnectionContribution()
        certificate = self._find_instance(connection.target_name, project)
        certificate.config._dns_validation = True
        result.merge(issued_certificate(certificate.name, project, self._renderer)[1])
        target_binding = next(
            item for item in bindings if item.certificate_name == certificate.name
        )
        for zone in sorted({record.zone_name for record in target_binding.records}):
            result.inputs.append(
                ModuleInput(
                    module=certificate.name,
                    name=f"dns_{zone}_validation_fqdns",
                    type="list(string)",
                    value=f"module.{zone}.acm_{certificate.name}_validation_fqdns",
                    description="Managed DNS validation record names",
                )
            )
        zone = connection.source_name
        records = {}
        for binding in bindings:
            selected = [
                record for record in binding.records if record.zone_name == zone
            ]
            if not selected:
                continue
            records.update({record.domain: record for record in selected})
            values = ", ".join(
                f'aws_route53_record.{zone}_acm_validation["{record.domain}"].fqdn'
                for record in selected
            )
            result.outputs.append(
                self._output(
                    zone,
                    f"acm_{binding.certificate_name}_validation_fqdns",
                    f"[{values}]",
                )
            )

        if records:
            owners = sorted({record.certificate_name for record in records.values()})
            for owner in owners:
                result.inputs.append(
                    ModuleInput(
                        module=zone,
                        name=f"acm_{owner}_validation_options",
                        type="set(object({ domain_name = string, resource_record_name = string, resource_record_type = string, resource_record_value = string }))",
                        value=f"module.{owner}.domain_validation_options",
                        description="Native ACM DNS validation options",
                    )
                )
            entries = {
                domain: {
                    "option": Expr(
                        f'[for dvo in var.acm_{record.certificate_name}_validation_options : dvo if lower(trimprefix(dvo.domain_name, "*.")) == "{domain}"][0]'
                    ),
                    "ttl": record.ttl,
                }
                for domain, record in sorted(records.items())
            }
            native_zone = f"aws_route53_zone.{zone}"
            zone_domain = next(iter(records.values())).zone_domain
            content = self._renderer.render_resource(
                "aws_route53_record",
                f"{zone}_acm_validation",
                {
                    "for_each": Expr(self._renderer.render_expression(entries)),
                    "zone_id": Expr(f"{native_zone}.zone_id"),
                    "name": Expr("each.value.option.resource_record_name"),
                    "type": Expr("each.value.option.resource_record_type"),
                    "records": [Expr("each.value.option.resource_record_value")],
                    "ttl": Expr("each.value.ttl"),
                    "lifecycle": {
                        "precondition": zone_dns_preconditions(zone, zone_domain)
                    },
                },
            )
            result.resources.append(self._resource(zone, "certificate_dns.tf", content))
        return result

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        resolve_certificate_dns(project)
        return [
            ConnectionIssue(
                severity="warning",
                message="Delegate each public hosted zone to its exported name servers before applying certificate consumers; validation records and issuance waiting are managed automatically. Existing validation CNAMEs must be imported before applying.",
            )
        ]
