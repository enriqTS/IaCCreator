"""Glue service generator — produces HCL for aws_glue_catalog_database resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class GlueGenerator:
    """Generates Terraform files for Glue catalog databases."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_glue_catalog_database resource."""
        attrs: dict = {"name": "var.database_name"}

        return self._r.render_resource(
            "aws_glue_catalog_database", instance.name, attrs
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a Glue catalog database."""
        parts = [
            self._r.render_variable(
                "database_name", "string", "Name of the Glue catalog database"
            ),
        ]
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a Glue catalog database."""
        parts = [
            self._r.render_output(
                "database_name",
                f"aws_glue_catalog_database.{instance.name}.name",
                "Name of the Glue catalog database",
            ),
            self._r.render_output(
                "catalog_id",
                f"aws_glue_catalog_database.{instance.name}.catalog_id",
                "Catalog ID of the Glue catalog database",
            ),
        ]
        return "\n".join(parts)
