from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.generators.organization_delegation import precondition
from app.models.input_models.organizations_config import OrganizationsConfig
from app.models.ir_models import ResourceInstanceIR


class OrganizationsGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, OrganizationsConfig)
        attrs = {
            "feature_set": Expr("var.feature_set"),
            "aws_service_access_principals": Expr("var.aws_service_access_principals"),
            "enabled_policy_types": Expr("var.enabled_policy_types"),
        }
        if config._delegated_service_principals:
            principals = self._r.render_expression(config._delegated_service_principals)
            attrs["aws_service_access_principals"] = Expr(
                f"sort(distinct(concat(var.aws_service_access_principals, {principals})))"
            )
            attrs["lifecycle"] = {
                "precondition": [
                    precondition(
                        'var.feature_set == "ALL"',
                        "Connected security delegation requires all organization features.",
                    )
                ]
            }
        return self._r.render_resource(
            "aws_organizations_organization",
            instance.name,
            attrs,
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, OrganizationsConfig)
        fields = [
            ("feature_set", "string", "Organization feature set"),
            ("enabled_policy_types", "list(string)", "Enabled policy types"),
            (
                "aws_service_access_principals",
                "list(string)",
                "Additional trusted service principals",
            ),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_organizations_organization.{instance.name}"
        outputs = [
            self._r.render_output("organization_id", f"{ref}.id", "Organization ID"),
            self._r.render_output("organization_arn", f"{ref}.arn", "Organization ARN"),
        ]
        if get_typed_config(
            instance, OrganizationsConfig
        )._delegated_service_principals:
            outputs.append(
                self._r.render_output(
                    "delegation_context",
                    self._r.render_expression(
                        {
                            "id": Expr(f"{ref}.id"),
                            "arn": Expr(f"{ref}.arn"),
                            "management_account_id": Expr(f"{ref}.master_account_id"),
                            "feature_set": Expr(f"{ref}.feature_set"),
                            "service_principals": Expr(
                                f"{ref}.aws_service_access_principals"
                            ),
                            "active_member_ids": Expr(
                                f'[for account in {ref}.non_master_accounts : account.id if account.state == "ACTIVE"]'
                            ),
                        }
                    ),
                    "Native organization context for member delegation",
                )
            )
        return "\n".join(outputs)
