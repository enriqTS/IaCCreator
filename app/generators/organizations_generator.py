from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.organizations_config import OrganizationsConfig
from app.models.ir_models import ResourceInstanceIR


class OrganizationsGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, OrganizationsConfig)
        return self._r.render_resource(
            "aws_organizations_organization",
            instance.name,
            {
                "feature_set": Expr("var.feature_set"),
                "aws_service_access_principals": Expr("[]"),
                "enabled_policy_types": Expr("var.enabled_policy_types"),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, OrganizationsConfig)
        fields = [
            ("feature_set", "string", "Organization feature set"),
            ("enabled_policy_types", "list(string)", "Enabled policy types"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_organizations_organization.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "organization_id", f"{ref}.id", "Organization ID"
                ),
                self._r.render_output(
                    "organization_arn", f"{ref}.arn", "Organization ARN"
                ),
            ]
        )
