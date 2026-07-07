"""Integration tests for FileTreeAssembler with terraform variables.

Validates Requirements 5.1 and 9.9:
- Generated file tree contains terraform.tfvars with correct variable entries
- backend.tf, provider.tf, versions.tf are present and correctly formatted
"""

from app.models.input_models import (
    ArchitectureDescription,
    EnvironmentConfig,
    GlobalTerraformConfig,
    ResourceConfig,
    ResourceInstance,
    ServiceType,
)
from app.services.file_tree_assembler import FileTreeAssembler
from app.services.ir_builder import IRBuilder


def _build_tree(**overrides) -> dict[str, str]:
    """Build a FileTree from an ArchitectureDescription with sensible defaults."""
    defaults = dict(
        project_name="myproject",
        environments=[EnvironmentConfig(name="dev", variables={})],
        resources=[
            ResourceInstance(
                name="my-func",
                service_type=ServiceType.LAMBDA,
                config=ResourceConfig(handler="index.handler", runtime="python3.12"),
            ),
        ],
        connections=[],
    )
    defaults.update(overrides)
    desc = ArchitectureDescription(**defaults)
    ir = IRBuilder().build(desc)
    return FileTreeAssembler().assemble(ir)


# ---------------------------------------------------------------------------
# Requirement 5.1: terraform.tfvars contains correct variable entries
# ---------------------------------------------------------------------------


class TestTfvarsInFileTree:
    """Test that terraform.tfvars is generated with correct variable entries."""

    def test_tfvars_file_exists_in_environment(self):
        tree = _build_tree(
            resources=[
                ResourceInstance(
                    name="my-func",
                    service_type=ServiceType.LAMBDA,
                    config=ResourceConfig(
                        handler="index.handler", runtime="python3.12"
                    ),
                    terraform_variables={"function_name": "hello"},
                ),
            ],
        )
        assert "myproject/environments/dev/terraform.tfvars" in tree

    def test_tfvars_contains_string_variable_quoted(self):
        tree = _build_tree(
            resources=[
                ResourceInstance(
                    name="my-func",
                    service_type=ServiceType.LAMBDA,
                    config=ResourceConfig(
                        handler="index.handler", runtime="python3.12"
                    ),
                    terraform_variables={"function_name": "hello"},
                ),
            ],
        )
        content = tree["myproject/environments/dev/terraform.tfvars"]
        assert 'my-func_function_name = "hello"' in content

    def test_tfvars_contains_number_variable_unquoted(self):
        tree = _build_tree(
            resources=[
                ResourceInstance(
                    name="my-func",
                    service_type=ServiceType.LAMBDA,
                    config=ResourceConfig(
                        handler="index.handler", runtime="python3.12"
                    ),
                    terraform_variables={"memory_size": 512},
                ),
            ],
        )
        content = tree["myproject/environments/dev/terraform.tfvars"]
        assert "my-func_memory_size = 512" in content
        assert '"512"' not in content

    def test_tfvars_contains_bool_variable_unquoted(self):
        tree = _build_tree(
            resources=[
                ResourceInstance(
                    name="my-bucket",
                    service_type=ServiceType.S3,
                    terraform_variables={"versioning_enabled": True},
                ),
            ],
        )
        content = tree["myproject/environments/dev/terraform.tfvars"]
        assert "my-bucket_versioning_enabled = true" in content

    def test_tfvars_prefixes_avoid_collision(self):
        tree = _build_tree(
            resources=[
                ResourceInstance(
                    name="func-a",
                    service_type=ServiceType.LAMBDA,
                    config=ResourceConfig(handler="h", runtime="python3.12"),
                    terraform_variables={"function_name": "alpha"},
                ),
                ResourceInstance(
                    name="func-b",
                    service_type=ServiceType.LAMBDA,
                    config=ResourceConfig(handler="h", runtime="python3.12"),
                    terraform_variables={"function_name": "beta"},
                ),
            ],
        )
        content = tree["myproject/environments/dev/terraform.tfvars"]
        assert 'func-a_function_name = "alpha"' in content
        assert 'func-b_function_name = "beta"' in content

    def test_tfvars_across_multiple_environments(self):
        tree = _build_tree(
            environments=[
                EnvironmentConfig(name="dev", variables={}),
                EnvironmentConfig(name="prod", variables={}),
            ],
            resources=[
                ResourceInstance(
                    name="my-func",
                    service_type=ServiceType.LAMBDA,
                    config=ResourceConfig(handler="h", runtime="python3.12"),
                    terraform_variables={"function_name": "fn"},
                ),
            ],
        )
        for env in ("dev", "prod"):
            content = tree[f"myproject/environments/{env}/terraform.tfvars"]
            assert 'my-func_function_name = "fn"' in content

    def test_variables_tf_has_corresponding_blocks(self):
        tree = _build_tree(
            resources=[
                ResourceInstance(
                    name="my-func",
                    service_type=ServiceType.LAMBDA,
                    config=ResourceConfig(handler="h", runtime="python3.12"),
                    terraform_variables={"function_name": "hello", "memory_size": 256},
                ),
            ],
        )
        content = tree["myproject/environments/dev/variables.tf"]
        assert 'variable "my-func_function_name"' in content
        assert 'variable "my-func_memory_size"' in content

    def test_empty_terraform_variables_no_extra_entries(self):
        tree = _build_tree(
            resources=[
                ResourceInstance(
                    name="my-func",
                    service_type=ServiceType.LAMBDA,
                    config=ResourceConfig(handler="h", runtime="python3.12"),
                    terraform_variables={},
                ),
            ],
        )
        content = tree["myproject/environments/dev/terraform.tfvars"]
        # Should not contain any prefixed variable lines
        assert "my-func_" not in content

    def test_mixed_service_types_in_tfvars(self):
        tree = _build_tree(
            resources=[
                ResourceInstance(
                    name="my-func",
                    service_type=ServiceType.LAMBDA,
                    config=ResourceConfig(handler="h", runtime="python3.12"),
                    terraform_variables={"function_name": "fn", "timeout": 30},
                ),
                ResourceInstance(
                    name="my-bucket",
                    service_type=ServiceType.S3,
                    terraform_variables={
                        "bucket_name": "bkt",
                        "versioning_enabled": False,
                    },
                ),
            ],
        )
        content = tree["myproject/environments/dev/terraform.tfvars"]
        assert 'my-func_function_name = "fn"' in content
        assert "my-func_timeout = 30" in content
        assert 'my-bucket_bucket_name = "bkt"' in content
        assert "my-bucket_versioning_enabled = false" in content


# ---------------------------------------------------------------------------
# Requirement 9.9: backend.tf, provider.tf, versions.tf present and correct
# ---------------------------------------------------------------------------


class TestGlobalConfigFilesInFileTree:
    """Test that backend.tf, provider.tf, versions.tf are generated correctly."""

    def test_global_config_files_exist(self):
        tree = _build_tree()
        base = "myproject/environments/dev"
        assert f"{base}/backend.tf" in tree
        assert f"{base}/provider.tf" in tree
        assert f"{base}/versions.tf" in tree

    def test_default_backend_is_local(self):
        tree = _build_tree()
        content = tree["myproject/environments/dev/backend.tf"]
        assert 'backend "local"' in content

    def test_s3_backend_configuration(self):
        tree = _build_tree(
            global_terraform_config=GlobalTerraformConfig(
                backend_type="s3",
                backend_config={
                    "bucket": "my-tf-state",
                    "key": "terraform.tfstate",
                    "region": "us-east-1",
                    "dynamodb_table": "tf-locks",
                },
            ),
        )
        content = tree["myproject/environments/dev/backend.tf"]
        assert 'backend "s3"' in content
        assert 'bucket = "my-tf-state"' in content
        assert 'key = "terraform.tfstate"' in content
        assert 'dynamodb_table = "tf-locks"' in content

    def test_provider_default_region(self):
        tree = _build_tree()
        content = tree["myproject/environments/dev/provider.tf"]
        assert 'provider "aws"' in content
        assert 'region = "us-east-1"' in content

    def test_provider_custom_region_and_profile(self):
        tree = _build_tree(
            global_terraform_config=GlobalTerraformConfig(
                provider_region="eu-west-1",
                provider_profile="prod-profile",
            ),
        )
        content = tree["myproject/environments/dev/provider.tf"]
        assert 'region = "eu-west-1"' in content
        assert 'profile = "prod-profile"' in content

    def test_versions_tf_has_required_providers(self):
        tree = _build_tree()
        content = tree["myproject/environments/dev/versions.tf"]
        assert "required_providers" in content
        assert 'source  = "hashicorp/aws"' in content

    def test_versions_tf_with_constraints(self):
        tree = _build_tree(
            global_terraform_config=GlobalTerraformConfig(
                terraform_version=">= 1.5.0",
                aws_provider_version="~> 5.0",
            ),
        )
        content = tree["myproject/environments/dev/versions.tf"]
        assert 'required_version = ">= 1.5.0"' in content
        assert 'version = "~> 5.0"' in content

    def test_global_config_files_in_every_environment(self):
        tree = _build_tree(
            environments=[
                EnvironmentConfig(name="dev", variables={}),
                EnvironmentConfig(name="staging", variables={}),
                EnvironmentConfig(name="prod", variables={}),
            ],
            global_terraform_config=GlobalTerraformConfig(
                backend_type="s3",
                backend_config={"bucket": "state"},
                provider_region="us-west-2",
            ),
        )
        for env in ("dev", "staging", "prod"):
            base = f"myproject/environments/{env}"
            assert f"{base}/backend.tf" in tree
            assert 'backend "s3"' in tree[f"{base}/backend.tf"]
            assert 'region = "us-west-2"' in tree[f"{base}/provider.tf"]
            assert "required_providers" in tree[f"{base}/versions.tf"]


class TestEndToEndIntegration:
    """Full pipeline integration: input → IR → file tree with all terraform variable files."""

    def test_full_pipeline_with_variables_and_global_config(self):
        desc = ArchitectureDescription(
            project_name="infra",
            environments=[
                EnvironmentConfig(name="dev", variables={"region": "us-east-1"}),
            ],
            resources=[
                ResourceInstance(
                    name="api",
                    service_type=ServiceType.API_GATEWAY,
                    terraform_variables={"api_name": "my-api", "protocol_type": "HTTP"},
                ),
                ResourceInstance(
                    name="handler",
                    service_type=ServiceType.LAMBDA,
                    config=ResourceConfig(handler="main.handler", runtime="python3.12"),
                    terraform_variables={
                        "function_name": "handler-fn",
                        "memory_size": 256,
                        "timeout": 10,
                    },
                ),
                ResourceInstance(
                    name="store",
                    service_type=ServiceType.DYNAMODB,
                    config=ResourceConfig(hash_key="pk"),
                    terraform_variables={
                        "table_name": "data-store",
                        "billing_mode": "PAY_PER_REQUEST",
                    },
                ),
            ],
            connections=[],
            global_terraform_config=GlobalTerraformConfig(
                backend_type="s3",
                backend_config={"bucket": "tf-state", "key": "state.tfstate"},
                provider_region="us-west-2",
                provider_profile="deploy",
                terraform_version=">= 1.5.0",
                aws_provider_version="~> 5.0",
            ),
        )
        ir = IRBuilder().build(desc)
        tree = FileTreeAssembler().assemble(ir)

        base = "infra/environments/dev"

        # terraform.tfvars has all resource variables
        tfvars = tree[f"{base}/terraform.tfvars"]
        assert 'api_api_name = "my-api"' in tfvars
        assert 'handler_function_name = "handler-fn"' in tfvars
        assert "handler_memory_size = 256" in tfvars
        assert "handler_timeout = 10" in tfvars
        assert 'store_table_name = "data-store"' in tfvars

        # variables.tf has corresponding variable blocks
        variables = tree[f"{base}/variables.tf"]
        assert 'variable "api_api_name"' in variables
        assert 'variable "handler_function_name"' in variables
        assert 'variable "store_table_name"' in variables

        # Global config files
        assert 'backend "s3"' in tree[f"{base}/backend.tf"]
        assert 'bucket = "tf-state"' in tree[f"{base}/backend.tf"]
        assert 'region = "us-west-2"' in tree[f"{base}/provider.tf"]
        assert 'profile = "deploy"' in tree[f"{base}/provider.tf"]
        assert 'required_version = ">= 1.5.0"' in tree[f"{base}/versions.tf"]
        assert 'version = "~> 5.0"' in tree[f"{base}/versions.tf"]
