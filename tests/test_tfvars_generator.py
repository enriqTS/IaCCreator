"""Unit and property tests for TfvarsGenerator.

Validates Requirements 5.2, 5.3, 5.4, 5.5, 5.6:
- String formatting: var_name = "value"
- Number formatting: var_name = 123 (unquoted)
- Bool formatting: var_name = true / var_name = false
- Prefix collision avoidance with multiple instances
- Property 3: Every variable in terraform.tfvars has a corresponding variable block in variables.tf
"""

import re

from hypothesis import given, settings
from hypothesis import strategies as st

from app.generators.tfvars_generator import TfvarsGenerator
from app.generators.variable_schemas import VARIABLE_SCHEMAS
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import ResourceInstanceIR


def _make_instance(
    name: str = "my_func",
    service_type: ServiceType = ServiceType.LAMBDA,
    terraform_variables: dict | None = None,
    **config_kwargs,
) -> ResourceInstanceIR:
    return ResourceInstanceIR(
        name=name,
        service_type=service_type,
        config=ResourceConfig(**config_kwargs),
        terraform_variables=terraform_variables or {},
    )


class TestStringFormatting:
    """Requirement 5.2: string values are quoted."""

    def test_string_value_is_quoted(self):
        gen = TfvarsGenerator()
        inst = _make_instance(terraform_variables={"function_name": "hello"})
        output = gen.generate_tfvars([inst])
        assert 'my_func_function_name = "hello"' in output

    def test_empty_string_value_is_quoted(self):
        gen = TfvarsGenerator()
        inst = _make_instance(terraform_variables={"function_name": ""})
        output = gen.generate_tfvars([inst])
        assert 'my_func_function_name = ""' in output

    def test_string_with_special_chars(self):
        gen = TfvarsGenerator()
        inst = _make_instance(terraform_variables={"handler": "src/index.handler"})
        output = gen.generate_tfvars([inst])
        assert 'my_func_handler = "src/index.handler"' in output


class TestNumberFormatting:
    """Requirement 5.3: number values are unquoted."""

    def test_integer_value_is_unquoted(self):
        gen = TfvarsGenerator()
        inst = _make_instance(terraform_variables={"memory_size": 256})
        output = gen.generate_tfvars([inst])
        assert "my_func_memory_size = 256" in output
        assert '"256"' not in output

    def test_zero_value_is_unquoted(self):
        gen = TfvarsGenerator()
        inst = _make_instance(terraform_variables={"timeout": 0})
        output = gen.generate_tfvars([inst])
        assert "my_func_timeout = 0" in output

    def test_float_value_is_unquoted(self):
        gen = TfvarsGenerator()
        inst = _make_instance(terraform_variables={"timeout": 3.5})
        output = gen.generate_tfvars([inst])
        assert "my_func_timeout = 3.5" in output
        assert '"3.5"' not in output


class TestBoolFormatting:
    """Requirement 5.4: bool values are unquoted true/false."""

    def test_true_value(self):
        gen = TfvarsGenerator()
        inst = _make_instance(
            name="my_bucket",
            service_type=ServiceType.S3,
            terraform_variables={"versioning_enabled": True},
        )
        output = gen.generate_tfvars([inst])
        assert "my_bucket_versioning_enabled = true" in output

    def test_false_value(self):
        gen = TfvarsGenerator()
        inst = _make_instance(
            name="my_bucket",
            service_type=ServiceType.S3,
            terraform_variables={"versioning_enabled": False},
        )
        output = gen.generate_tfvars([inst])
        assert "my_bucket_versioning_enabled = false" in output

    def test_bool_not_quoted(self):
        gen = TfvarsGenerator()
        inst = _make_instance(
            name="b",
            service_type=ServiceType.S3,
            terraform_variables={"versioning_enabled": True},
        )
        output = gen.generate_tfvars([inst])
        assert '"true"' not in output
        assert '"false"' not in output


class TestPrefixCollisionAvoidance:
    """Requirement 5.5: prefix variable names with instance name to avoid collisions."""

    def test_same_service_type_prefixed_differently(self):
        gen = TfvarsGenerator()
        inst1 = _make_instance(
            name="func_a", terraform_variables={"function_name": "alpha"}
        )
        inst2 = _make_instance(
            name="func_b", terraform_variables={"function_name": "beta"}
        )
        output = gen.generate_tfvars([inst1, inst2])
        assert 'func_a_function_name = "alpha"' in output
        assert 'func_b_function_name = "beta"' in output

    def test_different_service_types_prefixed(self):
        gen = TfvarsGenerator()
        inst1 = _make_instance(
            name="my_func", terraform_variables={"function_name": "fn"}
        )
        inst2 = _make_instance(
            name="my_bucket",
            service_type=ServiceType.S3,
            terraform_variables={"bucket_name": "bkt"},
        )
        output = gen.generate_tfvars([inst1, inst2])
        assert 'my_func_function_name = "fn"' in output
        assert 'my_bucket_bucket_name = "bkt"' in output

    def test_no_prefix_mode(self):
        gen = TfvarsGenerator()
        inst = _make_instance(terraform_variables={"function_name": "hello"})
        output = gen.generate_tfvars([inst], prefix=False)
        assert 'function_name = "hello"' in output
        assert "my_func_function_name" not in output

    def test_prefix_in_variables_tf_matches_tfvars(self):
        gen = TfvarsGenerator()
        inst1 = _make_instance(
            name="func_a", terraform_variables={"function_name": "alpha"}
        )
        inst2 = _make_instance(
            name="func_b", terraform_variables={"function_name": "beta"}
        )
        tfvars = gen.generate_tfvars([inst1, inst2])
        variables_tf = gen.generate_variables_tf([inst1, inst2])
        assert "func_a_function_name" in tfvars
        assert "func_b_function_name" in tfvars
        assert 'variable "func_a_function_name"' in variables_tf
        assert 'variable "func_b_function_name"' in variables_tf


class TestVariablesTfGeneration:
    """Requirement 5.6: generate corresponding variable blocks."""

    def test_variable_block_has_type_and_description(self):
        gen = TfvarsGenerator()
        inst = _make_instance(terraform_variables={"function_name": "hello"})
        output = gen.generate_variables_tf([inst])
        assert 'variable "my_func_function_name"' in output
        assert "type        = string" in output
        assert "description" in output

    def test_variable_block_includes_default_when_schema_has_one(self):
        gen = TfvarsGenerator()
        inst = _make_instance(terraform_variables={"memory_size": 256})
        output = gen.generate_variables_tf([inst])
        assert 'variable "my_func_memory_size"' in output
        assert "default     = 128" in output

    def test_no_variable_block_for_empty_instances(self):
        gen = TfvarsGenerator()
        inst = _make_instance(terraform_variables={})
        output = gen.generate_variables_tf([inst])
        assert output == ""

    def test_no_tfvars_for_empty_instances(self):
        gen = TfvarsGenerator()
        inst = _make_instance(terraform_variables={})
        output = gen.generate_tfvars([inst])
        assert output == ""


class TestMapAndListTypes:
    """Requirement 8.3: map and list Terraform types in _tf_type."""

    def test_map_type_produces_map_string(self):
        gen = TfvarsGenerator()
        inst = _make_instance(
            terraform_variables={"tags": "placeholder"},
        )
        output = gen.generate_variables_tf([inst])
        assert "type        = map(string)" in output

    def test_list_type_produces_list_string(self):
        gen = TfvarsGenerator()
        inst = _make_instance(
            terraform_variables={"layers": "placeholder"},
        )
        output = gen.generate_variables_tf([inst])
        assert "type        = list(string)" in output

    def test_map_variable_has_description_from_schema(self):
        gen = TfvarsGenerator()
        inst = _make_instance(
            terraform_variables={"environment_variables": "placeholder"},
        )
        output = gen.generate_variables_tf([inst])
        assert "Environment variables for the Lambda function" in output

    def test_list_variable_has_description_from_schema(self):
        gen = TfvarsGenerator()
        inst = _make_instance(
            terraform_variables={"layers": "placeholder"},
        )
        output = gen.generate_variables_tf([inst])
        assert "List of Lambda layer ARNs" in output

    def test_unknown_type_falls_back_to_string(self):
        assert TfvarsGenerator._tf_type("unknown") == "string"

    def test_all_five_types_mapped(self):
        assert TfvarsGenerator._tf_type("string") == "string"
        assert TfvarsGenerator._tf_type("number") == "number"
        assert TfvarsGenerator._tf_type("bool") == "bool"
        assert TfvarsGenerator._tf_type("map") == "map(string)"
        assert TfvarsGenerator._tf_type("list") == "list(string)"


class TestMixedTypes:
    """Test generation with a mix of string, number, and bool variables."""

    def test_all_types_in_single_instance(self):
        gen = TfvarsGenerator()
        inst = _make_instance(
            terraform_variables={
                "function_name": "my-fn",
                "memory_size": 512,
                "timeout": 30,
            }
        )
        output = gen.generate_tfvars([inst])
        assert 'my_func_function_name = "my-fn"' in output
        assert "my_func_memory_size = 512" in output
        assert "my_func_timeout = 30" in output

    def test_s3_mixed_types(self):
        gen = TfvarsGenerator()
        inst = _make_instance(
            name="bucket",
            service_type=ServiceType.S3,
            terraform_variables={"bucket_name": "my-bkt", "versioning_enabled": True},
        )
        output = gen.generate_tfvars([inst])
        assert 'bucket_bucket_name = "my-bkt"' in output
        assert "bucket_versioning_enabled = true" in output


# ---------------------------------------------------------------------------
# Property 3: Every variable in terraform.tfvars has a corresponding
#             variable block in variables.tf
# ---------------------------------------------------------------------------

# Strategy: generate a list of ResourceInstanceIR with random terraform_variables
_service_types_with_schemas = [st for st in ServiceType if st in VARIABLE_SCHEMAS]

_tf_var_value_st = st.one_of(
    st.text(min_size=0, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_"),
    st.integers(min_value=0, max_value=10000),
    st.booleans(),
)


@st.composite
def resource_instance_ir_strategy(draw):
    """Generate a ResourceInstanceIR with random terraform_variables from its schema."""
    svc = draw(st.sampled_from(_service_types_with_schemas))
    name = draw(st.from_regex(r"[a-z][a-z0-9_]{0,9}", fullmatch=True))
    schema = VARIABLE_SCHEMAS[svc]
    var_names = [s.name for s in schema]
    # Pick a random subset of variables to include
    chosen = draw(
        st.lists(
            st.sampled_from(var_names), min_size=1, max_size=len(var_names), unique=True
        )
    )
    variables = {vn: draw(_tf_var_value_st) for vn in chosen}
    return ResourceInstanceIR(
        name=name,
        service_type=svc,
        config=ResourceConfig(),
        terraform_variables=variables,
    )


@given(
    instances=st.lists(
        resource_instance_ir_strategy(),
        min_size=1,
        max_size=5,
    ).filter(lambda insts: len({i.name for i in insts}) == len(insts))
)
@settings(max_examples=50)
def test_property_3_tfvars_variables_tf_correspondence(instances):
    """Property 3: Every variable name in terraform.tfvars has a corresponding
    variable block in variables.tf. This ensures no variable is referenced
    without being declared."""
    gen = TfvarsGenerator()
    tfvars_output = gen.generate_tfvars(instances)
    variables_tf_output = gen.generate_variables_tf(instances)

    # Extract variable names from tfvars (left side of '=')
    tfvar_names = set()
    for line in tfvars_output.strip().splitlines():
        line = line.strip()
        if line and "=" in line:
            var_name = line.split("=")[0].strip()
            tfvar_names.add(var_name)

    # Extract variable names from variables.tf (inside variable "..." blocks)
    declared_names = set(re.findall(r'variable\s+"([^"]+)"', variables_tf_output))

    # Every tfvar must have a declaration
    assert tfvar_names <= declared_names, (
        f"Variables in tfvars without declaration: {tfvar_names - declared_names}"
    )


# ---------------------------------------------------------------------------
# Feature: enhanced-variable-configuration, Property 13: TfvarsGenerator
# produces entries for all terraform_variables
# ---------------------------------------------------------------------------


@given(instance=resource_instance_ir_strategy())
@settings(max_examples=50)
def test_property_13_tfvars_entries_for_all_terraform_variables(instance):
    """Property 13: TfvarsGenerator produces entries for all terraform_variables.

    For any ResourceInstanceIR with terraform_variables set, the TfvarsGenerator
    shall produce a terraform.tfvars entry and a matching variable block for every
    key in terraform_variables, using the type and description from VARIABLE_SCHEMAS.

    **Validates: Requirements 8.3**
    """
    gen = TfvarsGenerator()
    tfvars_output = gen.generate_tfvars([instance])
    variables_tf_output = gen.generate_variables_tf([instance])

    for var_key in instance.terraform_variables:
        prefixed_name = f"{instance.name}_{var_key}"

        # tfvars must contain an assignment line for this variable
        assert prefixed_name in tfvars_output, (
            f"Missing tfvars entry for '{prefixed_name}'. "
            f"terraform_variables keys: {list(instance.terraform_variables.keys())}"
        )

        # variables.tf must contain a variable block for this variable
        assert f'variable "{prefixed_name}"' in variables_tf_output, (
            f"Missing variable block for '{prefixed_name}'. "
            f"terraform_variables keys: {list(instance.terraform_variables.keys())}"
        )
