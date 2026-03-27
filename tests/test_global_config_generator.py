"""Unit tests for GlobalConfigGenerator."""

import pytest

from app.generators.global_config_generator import GlobalConfigGenerator
from app.models.ir_models import GlobalTerraformConfigIR


@pytest.fixture
def gen() -> GlobalConfigGenerator:
    return GlobalConfigGenerator()


# ---------------------------------------------------------------------------
# backend.tf tests
# ---------------------------------------------------------------------------

class TestBackendS3:
    def test_s3_backend_block_structure(self, gen: GlobalConfigGenerator):
        config = GlobalTerraformConfigIR(
            backend_type="s3",
            backend_config={
                "bucket": "my-tf-state",
                "key": "terraform.tfstate",
                "region": "us-east-1",
                "dynamodb_table": "tf-locks",
            },
        )
        result = gen.generate_backend_tf(config)

        assert 'backend "s3"' in result
        assert 'bucket = "my-tf-state"' in result
        assert 'key = "terraform.tfstate"' in result
        assert 'region = "us-east-1"' in result
        assert 'dynamodb_table = "tf-locks"' in result
        # Outer terraform block
        assert result.startswith("terraform {")
        assert result.strip().endswith("}")

    def test_s3_backend_indentation(self, gen: GlobalConfigGenerator):
        config = GlobalTerraformConfigIR(
            backend_type="s3",
            backend_config={"bucket": "state-bucket"},
        )
        result = gen.generate_backend_tf(config)
        lines = result.splitlines()

        # backend line should be indented once
        assert lines[1].startswith("  backend")
        # config key should be indented twice
        assert lines[2].startswith("    bucket")


class TestBackendLocal:
    def test_local_backend_empty_config(self, gen: GlobalConfigGenerator):
        config = GlobalTerraformConfigIR(backend_type="local", backend_config={})
        result = gen.generate_backend_tf(config)

        assert 'backend "local"' in result
        assert result.startswith("terraform {")
        assert result.strip().endswith("}")

    def test_local_backend_with_path(self, gen: GlobalConfigGenerator):
        config = GlobalTerraformConfigIR(
            backend_type="local",
            backend_config={"path": "relative/terraform.tfstate"},
        )
        result = gen.generate_backend_tf(config)

        assert 'backend "local"' in result
        assert 'path = "relative/terraform.tfstate"' in result


# ---------------------------------------------------------------------------
# provider.tf tests
# ---------------------------------------------------------------------------

class TestProviderWithProfile:
    def test_provider_includes_profile(self, gen: GlobalConfigGenerator):
        config = GlobalTerraformConfigIR(
            provider_region="eu-west-1",
            provider_profile="my-profile",
        )
        result = gen.generate_provider_tf(config)

        assert 'provider "aws"' in result
        assert 'region = "eu-west-1"' in result
        assert 'profile = "my-profile"' in result


class TestProviderWithoutProfile:
    def test_provider_omits_profile(self, gen: GlobalConfigGenerator):
        config = GlobalTerraformConfigIR(provider_region="us-west-2")
        result = gen.generate_provider_tf(config)

        assert 'provider "aws"' in result
        assert 'region = "us-west-2"' in result
        assert "profile" not in result

    def test_provider_default_region(self, gen: GlobalConfigGenerator):
        config = GlobalTerraformConfigIR()
        result = gen.generate_provider_tf(config)

        assert 'region = "us-east-1"' in result


# ---------------------------------------------------------------------------
# versions.tf tests
# ---------------------------------------------------------------------------

class TestVersionsWithConstraints:
    def test_versions_with_both_constraints(self, gen: GlobalConfigGenerator):
        config = GlobalTerraformConfigIR(
            terraform_version=">= 1.5.0",
            aws_provider_version="~> 5.0",
        )
        result = gen.generate_versions_tf(config)

        assert 'required_version = ">= 1.5.0"' in result
        assert 'source  = "hashicorp/aws"' in result
        assert 'version = "~> 5.0"' in result
        assert result.startswith("terraform {")

    def test_versions_with_only_terraform_version(self, gen: GlobalConfigGenerator):
        config = GlobalTerraformConfigIR(terraform_version=">= 1.5.0")
        result = gen.generate_versions_tf(config)

        assert 'required_version = ">= 1.5.0"' in result
        assert 'source  = "hashicorp/aws"' in result
        assert "version" not in result.split("required_providers")[1].split("source")[0]

    def test_versions_with_only_provider_version(self, gen: GlobalConfigGenerator):
        config = GlobalTerraformConfigIR(aws_provider_version="~> 5.0")
        result = gen.generate_versions_tf(config)

        assert "required_version" not in result
        assert 'version = "~> 5.0"' in result


class TestVersionsWithoutConstraints:
    def test_versions_no_constraints(self, gen: GlobalConfigGenerator):
        config = GlobalTerraformConfigIR()
        result = gen.generate_versions_tf(config)

        assert "required_version" not in result
        assert 'source  = "hashicorp/aws"' in result
        # version line should not appear when aws_provider_version is None
        lines = result.splitlines()
        version_lines = [l for l in lines if "version" in l.lower() and "required_version" not in l and "required_providers" not in l]
        # Only the source line should reference "hashicorp/aws", no version = "..." line
        for line in version_lines:
            assert "source" in line or "required" in line

    def test_versions_always_has_required_providers_block(self, gen: GlobalConfigGenerator):
        config = GlobalTerraformConfigIR()
        result = gen.generate_versions_tf(config)

        assert "required_providers" in result
        assert "hashicorp/aws" in result
