"""TfvarsGenerator — produces terraform.tfvars and variables.tf from resource variable values."""

from app.generators.hcl_renderer import HCLRenderer
from app.generators.variable_schemas import VARIABLE_SCHEMAS
from app.models.ir_models import ResourceInstanceIR


class TfvarsGenerator:
    """Generates terraform.tfvars and corresponding variables.tf from resource variable values."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_tfvars(
        self, instances: list[ResourceInstanceIR], prefix: bool = True
    ) -> str:
        """Generate terraform.tfvars content with properly typed values.

        Strings are quoted, numbers and bools are unquoted.
        When *prefix* is True, variable names are prefixed with the instance name
        to avoid collisions across multiple resources.
        """
        lines: list[str] = []
        for instance in instances:
            if not instance.terraform_variables:
                continue
            for var_name, value in instance.terraform_variables.items():
                full_name = f"{instance.name}_{var_name}" if prefix else var_name
                lines.append(f"{full_name} = {self._format_tfvar_value(value)}")
        return "\n".join(lines) + "\n" if lines else ""

    def generate_variables_tf(
        self, instances: list[ResourceInstanceIR], prefix: bool = True
    ) -> str:
        """Generate variable blocks matching the tfvars entries.

        Each variable in terraform.tfvars gets a corresponding ``variable`` block
        with the correct type and description sourced from the schema.
        """
        blocks: list[str] = []
        for instance in instances:
            if not instance.terraform_variables:
                continue
            schema_list = VARIABLE_SCHEMAS.get(instance.service_type, [])
            schema_map = {s.name: s for s in schema_list}

            for var_name in instance.terraform_variables:
                full_name = f"{instance.name}_{var_name}" if prefix else var_name
                schema = schema_map.get(var_name)
                var_type = self._tf_type(schema.type if schema else "string")
                description = schema.description if schema else var_name
                default = schema.default if schema else None
                blocks.append(
                    self._r.render_variable(
                        full_name, var_type, description, default=default
                    )
                )
        return "\n".join(blocks) if blocks else ""

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_tfvar_value(value: str | int | float | bool) -> str:
        """Format a Python value as an HCL tfvars literal."""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        return f'"{value}"'

    @staticmethod
    def _tf_type(schema_type: str) -> str:
        """Map schema type strings to Terraform type keywords."""
        return {
            "string": "string",
            "number": "number",
            "bool": "bool",
            "map": "map(string)",
            "list": "list(string)",
        }.get(schema_type, "string")
