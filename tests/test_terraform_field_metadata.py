"""Unit tests for TerraformField metadata infrastructure and get_variable_schema().

Validates that:
- TerraformField metadata is correctly stored in Pydantic FieldInfo
- get_terraform_meta() retrieves metadata from annotated fields
- BaseServiceConfig.get_variable_schema() produces correct VariableSchemaEntry lists
- Type inference works for common Python types
- Fields without TerraformField are excluded from schema output
- ConnectionInput and get_connections_schema() work as expected
"""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._connections import ConnectionInput
from app.models.input_models._metadata import (
    OptionEntry,
    TerraformField,
    ValidationRule,
    VariableSchemaEntry,
    VisibleWhen,
    _infer_tf_type,
    get_terraform_meta,
)

# ---------------------------------------------------------------------------
# Test models (used only in this test file)
# ---------------------------------------------------------------------------


class MinimalConfig(BaseServiceConfig):
    """Minimal config with a single TerraformField."""

    function_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the function",
    )


class FullConfig(BaseServiceConfig):
    """Config exercising all TerraformField features."""

    runtime: str | None = TerraformField(
        "python3.12",
        group="General",
        description="Lambda function runtime",
        options=[
            OptionEntry(value="python3.12", label="Python 3.12", group="Python"),
            OptionEntry(value="nodejs20.x", label="Node.js 20.x", group="Node.js"),
        ],
    )
    memory_size: int | None = TerraformField(
        128,
        group="Performance",
        description="Memory in MB",
        validation=ValidationRule(min=128, max=10240),
    )
    read_capacity: int | None = TerraformField(
        5,
        group="Capacity",
        description="Provisioned read capacity units",
        validation=ValidationRule(min=1, max=40000),
        visible_when=VisibleWhen(field="billing_mode", equals="PROVISIONED"),
    )
    billing_mode: str | None = TerraformField(
        "PAY_PER_REQUEST",
        group="General",
        description="Billing mode",
        options=[
            OptionEntry(value="PAY_PER_REQUEST", label="On-Demand"),
            OptionEntry(value="PROVISIONED", label="Provisioned"),
        ],
    )
    layers: list[str] | None = TerraformField(
        None,
        group="Deployment",
        description="Lambda layer ARNs",
        tf_type="list",
    )
    env_vars: dict[str, str] | None = TerraformField(
        None,
        group="Metadata",
        description="Environment variables",
    )
    publish: bool | None = TerraformField(
        False,
        group="Deployment",
        description="Publish as new version",
    )


class MixedConfig(BaseServiceConfig):
    """Config with both TerraformField and plain fields."""

    service_type: Literal["test"] = "test"
    # This field has TerraformField metadata
    bucket_name: str | None = TerraformField(
        None,
        group="General",
        description="S3 bucket name",
    )
    # This field does NOT have TerraformField metadata (plain Pydantic field)
    internal_flag: bool = False


class WithConnectionsConfig(BaseServiceConfig):
    """Config that declares connection inputs."""

    api_name: str | None = TerraformField(
        None,
        group="General",
        description="API name",
    )

    @classmethod
    def get_connections_schema(cls) -> list[ConnectionInput]:
        return [
            ConnectionInput(
                name="lambda_invoke_arn",
                source_service_type="lambda",
                description="Lambda invoke ARN for integration",
                tf_variable_name="lambda_invoke_arn",
                connection_role="route_handler",
            ),
            ConnectionInput(
                name="authorizer_lambda_arn",
                source_service_type="lambda",
                description="Lambda ARN for authorizer",
                tf_variable_name="authorizer_lambda_invoke_arn",
                connection_role="authorizer",
            ),
        ]


# ---------------------------------------------------------------------------
# Tests: TerraformField and get_terraform_meta
# ---------------------------------------------------------------------------


class TestTerraformFieldMetadata:
    """Test that TerraformField stores metadata correctly in Pydantic FieldInfo."""

    def test_basic_metadata_stored(self) -> None:
        field_info = MinimalConfig.model_fields["function_name"]
        meta = get_terraform_meta(field_info)
        assert meta is not None
        assert meta.group == "General"

    def test_options_stored(self) -> None:
        field_info = FullConfig.model_fields["runtime"]
        meta = get_terraform_meta(field_info)
        assert meta is not None
        assert meta.options is not None
        assert len(meta.options) == 2
        assert meta.options[0].value == "python3.12"
        assert meta.options[0].label == "Python 3.12"
        assert meta.options[0].group == "Python"

    def test_validation_stored(self) -> None:
        field_info = FullConfig.model_fields["memory_size"]
        meta = get_terraform_meta(field_info)
        assert meta is not None
        assert meta.validation is not None
        assert meta.validation.min == 128
        assert meta.validation.max == 10240

    def test_visible_when_stored(self) -> None:
        field_info = FullConfig.model_fields["read_capacity"]
        meta = get_terraform_meta(field_info)
        assert meta is not None
        assert meta.visible_when is not None
        assert meta.visible_when.field == "billing_mode"
        assert meta.visible_when.equals == "PROVISIONED"

    def test_tf_type_override_stored(self) -> None:
        field_info = FullConfig.model_fields["layers"]
        meta = get_terraform_meta(field_info)
        assert meta is not None
        assert meta.tf_type == "list"

    def test_no_metadata_returns_none(self) -> None:
        field_info = MixedConfig.model_fields["internal_flag"]
        meta = get_terraform_meta(field_info)
        assert meta is None

    def test_service_type_field_has_no_metadata(self) -> None:
        field_info = MixedConfig.model_fields["service_type"]
        meta = get_terraform_meta(field_info)
        assert meta is None

    def test_base_fields_have_no_metadata(self) -> None:
        """Fields inherited from BaseServiceConfig (tags, description, env_vars) have no TF metadata."""
        field_info = MinimalConfig.model_fields["tags"]
        meta = get_terraform_meta(field_info)
        assert meta is None


# ---------------------------------------------------------------------------
# Tests: _infer_tf_type
# ---------------------------------------------------------------------------


class TestInferTfType:
    """Test Python type → Terraform type inference."""

    def test_str(self) -> None:
        assert _infer_tf_type(str) == "string"

    def test_int(self) -> None:
        assert _infer_tf_type(int) == "number"

    def test_float(self) -> None:
        assert _infer_tf_type(float) == "number"

    def test_bool(self) -> None:
        assert _infer_tf_type(bool) == "bool"

    def test_dict(self) -> None:
        assert _infer_tf_type(dict) == "map"
        assert _infer_tf_type(dict[str, str]) == "map"

    def test_list(self) -> None:
        assert _infer_tf_type(list) == "list"
        assert _infer_tf_type(list[str]) == "list"

    def test_optional_str(self) -> None:
        assert _infer_tf_type(Optional[str]) == "string"

    def test_optional_int(self) -> None:
        assert _infer_tf_type(Optional[int]) == "number"

    def test_optional_bool(self) -> None:
        assert _infer_tf_type(Optional[bool]) == "bool"

    def test_optional_list(self) -> None:
        assert _infer_tf_type(Optional[list[str]]) == "list"

    def test_optional_dict(self) -> None:
        assert _infer_tf_type(Optional[dict[str, str]]) == "map"


# ---------------------------------------------------------------------------
# Tests: get_variable_schema()
# ---------------------------------------------------------------------------


class TestGetVariableSchema:
    """Test BaseServiceConfig.get_variable_schema() introspection."""

    def test_minimal_config_produces_one_entry(self) -> None:
        schema = MinimalConfig.get_variable_schema()
        assert len(schema) == 1
        entry = schema[0]
        assert entry.name == "function_name"
        assert entry.type == "string"
        assert entry.description == "Name of the function"
        assert entry.group == "General"
        assert entry.default is None

    def test_full_config_produces_all_annotated_entries(self) -> None:
        schema = FullConfig.get_variable_schema()
        names = [e.name for e in schema]
        assert "runtime" in names
        assert "memory_size" in names
        assert "read_capacity" in names
        assert "billing_mode" in names
        assert "layers" in names
        assert "env_vars" in names
        assert "publish" in names

    def test_full_config_entry_details(self) -> None:
        schema = FullConfig.get_variable_schema()
        by_name = {e.name: e for e in schema}

        # runtime
        runtime = by_name["runtime"]
        assert runtime.type == "string"
        assert runtime.default == "python3.12"
        assert runtime.group == "General"
        assert runtime.options is not None
        assert len(runtime.options) == 2

        # memory_size
        mem = by_name["memory_size"]
        assert mem.type == "number"
        assert mem.default == 128
        assert mem.group == "Performance"
        assert mem.validation is not None
        assert mem.validation.min == 128

        # read_capacity (visible_when)
        rc = by_name["read_capacity"]
        assert rc.visible_when is not None
        assert rc.visible_when.field == "billing_mode"
        assert rc.visible_when.equals == "PROVISIONED"

        # layers (tf_type override)
        layers = by_name["layers"]
        assert layers.type == "list"

        # env_vars (dict → map)
        env = by_name["env_vars"]
        assert env.type == "map"

        # publish (bool)
        pub = by_name["publish"]
        assert pub.type == "bool"
        assert pub.default is False

    def test_mixed_config_excludes_non_terraform_fields(self) -> None:
        schema = MixedConfig.get_variable_schema()
        names = [e.name for e in schema]
        assert "bucket_name" in names
        assert "internal_flag" not in names
        assert "service_type" not in names
        # Base fields without TerraformField are also excluded
        assert "tags" not in names
        assert "description" not in names

    def test_base_service_config_returns_empty(self) -> None:
        """BaseServiceConfig itself has no TerraformField-annotated fields."""
        schema = BaseServiceConfig.get_variable_schema()
        assert schema == []

    def test_schema_entries_are_variable_schema_entry_instances(self) -> None:
        schema = FullConfig.get_variable_schema()
        for entry in schema:
            assert isinstance(entry, VariableSchemaEntry)

    def test_has_terraform_schema_true(self) -> None:
        assert FullConfig.has_terraform_schema() is True
        assert MinimalConfig.has_terraform_schema() is True
        assert MixedConfig.has_terraform_schema() is True

    def test_has_terraform_schema_false(self) -> None:
        assert BaseServiceConfig.has_terraform_schema() is False


# ---------------------------------------------------------------------------
# Tests: get_connections_schema()
# ---------------------------------------------------------------------------


class TestGetConnectionsSchema:
    """Test connection input declarations."""

    def test_default_returns_empty(self) -> None:
        assert BaseServiceConfig.get_connections_schema() == []
        assert MinimalConfig.get_connections_schema() == []

    def test_override_returns_connections(self) -> None:
        conns = WithConnectionsConfig.get_connections_schema()
        assert len(conns) == 2
        assert all(isinstance(c, ConnectionInput) for c in conns)

    def test_connection_input_details(self) -> None:
        conns = WithConnectionsConfig.get_connections_schema()
        handler = conns[0]
        assert handler.name == "lambda_invoke_arn"
        assert handler.source_service_type == "lambda"
        assert handler.tf_variable_name == "lambda_invoke_arn"
        assert handler.connection_role == "route_handler"

        auth = conns[1]
        assert auth.name == "authorizer_lambda_arn"
        assert auth.connection_role == "authorizer"


# ---------------------------------------------------------------------------
# Tests: VariableSchemaEntry serialization (matches API output format)
# ---------------------------------------------------------------------------


class TestVariableSchemaEntrySerialization:
    """Ensure schema entries serialize to the expected JSON format."""

    def test_minimal_entry_serialization(self) -> None:
        entry = VariableSchemaEntry(
            name="bucket_name",
            type="string",
            description="Name of the S3 bucket",
            group="General",
        )
        data = entry.model_dump(exclude_none=True)
        assert data == {
            "name": "bucket_name",
            "type": "string",
            "description": "Name of the S3 bucket",
            "group": "General",
        }

    def test_full_entry_serialization(self) -> None:
        entry = VariableSchemaEntry(
            name="memory_size",
            type="number",
            description="Memory in MB",
            default=128,
            group="Performance",
            validation=ValidationRule(min=128, max=10240),
            visible_when=VisibleWhen(field="billing_mode", equals="PROVISIONED"),
            options=[OptionEntry(value=128, label="128 MB")],
        )
        data = entry.model_dump(exclude_none=True)
        assert data["name"] == "memory_size"
        assert data["default"] == 128
        assert data["validation"]["min"] == 128
        assert data["visible_when"]["field"] == "billing_mode"
        assert len(data["options"]) == 1
