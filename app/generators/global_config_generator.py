"""GlobalConfigGenerator — produces backend.tf, provider.tf, and versions.tf."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import GlobalTerraformConfigIR


class GlobalConfigGenerator:
    """Generates backend.tf, provider.tf, and versions.tf from GlobalTerraformConfigIR."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_backend_tf(self, config: GlobalTerraformConfigIR) -> str:
        """Produce backend.tf with a ``terraform { backend "..." { ... } }`` block."""
        indent = self._r.INDENT
        lines = ["terraform {"]
        lines.append(f'{indent}backend "{config.backend_type}" {{')
        for key, value in config.backend_config.items():
            lines.append(f"{indent}{indent}{key} = {self._r._quote(value)}")
        lines.append(f"{indent}}}")
        lines.append("}")
        return "\n".join(lines) + "\n"

    def generate_provider_tf(self, config: GlobalTerraformConfigIR) -> str:
        """Produce provider.tf with an AWS provider block (region, optional profile)."""
        indent = self._r.INDENT
        lines = ['provider "aws" {']
        lines.append(f'{indent}region = "{config.provider_region}"')
        if config.provider_profile:
            lines.append(f'{indent}profile = "{config.provider_profile}"')
        lines.append("}")
        return "\n".join(lines) + "\n"

    def generate_versions_tf(self, config: GlobalTerraformConfigIR) -> str:
        """Produce versions.tf with required_version and required_providers."""
        indent = self._r.INDENT
        indent2 = indent * 2
        indent3 = indent * 3
        lines = ["terraform {"]

        if config.terraform_version:
            lines.append(f'{indent}required_version = "{config.terraform_version}"')
            lines.append("")

        lines.append(f"{indent}required_providers {{")
        lines.append(f"{indent2}aws = {{")
        lines.append(f'{indent3}source  = "hashicorp/aws"')
        if config.aws_provider_version:
            lines.append(f'{indent3}version = "{config.aws_provider_version}"')
        lines.append(f"{indent2}}}")
        lines.append(f"{indent}}}")

        lines.append("}")
        return "\n".join(lines) + "\n"
