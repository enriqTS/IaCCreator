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

    def generate_provider_tf(
        self,
        config: GlobalTerraformConfigIR,
        default_region: str | None = None,
        regions: set[str] | None = None,
    ) -> str:
        """Produce the default provider and deterministic aliases for other Regions."""
        indent = self._r.INDENT
        default = default_region or config.provider_region
        configured_regions = sorted((regions or set()) | {default})
        blocks = [self._provider_block(config, default, None, indent)]
        blocks.extend(
            self._provider_block(config, region, self.provider_alias(region), indent)
            for region in configured_regions
            if region != default
        )
        return "\n\n".join(blocks) + "\n"

    @staticmethod
    def provider_alias(region: str) -> str:
        return region.replace("-", "_")

    @staticmethod
    def _provider_block(
        config: GlobalTerraformConfigIR,
        region: str,
        alias: str | None,
        indent: str,
    ) -> str:
        lines = ['provider "aws" {']
        if alias:
            lines.append(f'{indent}alias = "{alias}"')
        lines.append(f'{indent}region = "{region}"')
        if config.provider_profile:
            lines.append(f'{indent}profile = "{config.provider_profile}"')
        lines.append("}")
        return "\n".join(lines)

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
