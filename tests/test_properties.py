"""Property-based tests for Terraform IaC Generator."""

import re

from hypothesis import given, settings
from hypothesis import strategies as st

from app.generators.hcl_renderer import HCLRenderer
from app.generators.service_category_map import get_category

# --- Hypothesis strategies for HCL renderer inputs ---

# Simple identifiers for block/variable/output names
_identifier_st = st.from_regex(r"[a-z][a-z0-9_]{0,19}", fullmatch=True)

# Simple string values (no newlines to keep HCL single-line values valid)
_simple_str_st = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S"), blacklist_characters='\n\r"\\'
    ),
    min_size=1,
    max_size=30,
)

# Flat attribute dicts (string/int/bool values)
_flat_value_st = st.one_of(
    _simple_str_st,
    st.integers(min_value=0, max_value=9999),
    st.booleans(),
)

_flat_attrs_st = st.dictionaries(
    keys=_identifier_st,
    values=_flat_value_st,
    min_size=1,
    max_size=6,
)

# Nested attribute dicts (one level of nesting)
_nested_attrs_st = st.dictionaries(
    keys=_identifier_st,
    values=st.one_of(
        _flat_value_st,
        st.dictionaries(
            keys=_identifier_st, values=_flat_value_st, min_size=1, max_size=3
        ),
    ),
    min_size=1,
    max_size=6,
)

_var_type_st = st.sampled_from(
    ["string", "number", "bool", "list(string)", "map(string)"]
)

_region_st = st.sampled_from(["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"])


# --- Indentation checker ---

TWO_SPACE_RE = re.compile(r"^( *)(\S.*)$")


def _assert_two_space_indentation(hcl: str) -> None:
    """Assert every indented line in *hcl* uses multiples of two spaces (no tabs)."""
    for lineno, line in enumerate(hcl.splitlines(), start=1):
        if not line or line.isspace():
            continue
        assert "\t" not in line, f"Tab found on line {lineno}: {line!r}"
        m = TWO_SPACE_RE.match(line)
        assert m, f"Line {lineno} has unexpected format: {line!r}"
        leading = m.group(1)
        assert len(leading) % 2 == 0, (
            f"Line {lineno} has {len(leading)}-space indent (not a multiple of 2): {line!r}"
        )


# --- Property 12: Two-space indentation ---
# Feature: terraform-iac-generator, Property 12: Two-space indentation
# Validates: Requirements 7.4


renderer = HCLRenderer()


@settings(max_examples=100)
@given(block_type=_identifier_st, name=_identifier_st, attrs=_nested_attrs_st)
def test_property_12_render_resource_two_space_indent(block_type, name, attrs):
    """render_resource output uses only two-space indentation."""
    hcl = renderer.render_resource(block_type, name, attrs)
    _assert_two_space_indentation(hcl)


@settings(max_examples=100)
@given(name=_identifier_st, var_type=_var_type_st, description=_simple_str_st)
def test_property_12_render_variable_two_space_indent(name, var_type, description):
    """render_variable output uses only two-space indentation."""
    hcl = renderer.render_variable(name, var_type, description)
    _assert_two_space_indentation(hcl)


@settings(max_examples=100)
@given(name=_identifier_st, value=_simple_str_st, description=_simple_str_st)
def test_property_12_render_output_two_space_indent(name, value, description):
    """render_output output uses only two-space indentation."""
    hcl = renderer.render_output(name, value, description)
    _assert_two_space_indentation(hcl)


@settings(max_examples=100)
@given(
    name=_identifier_st,
    source=_simple_str_st,
    variables=st.dictionaries(
        keys=_identifier_st, values=_simple_str_st, min_size=0, max_size=5
    ),
)
def test_property_12_render_module_two_space_indent(name, source, variables):
    """render_module output uses only two-space indentation."""
    hcl = renderer.render_module(name, source, variables)
    _assert_two_space_indentation(hcl)


@settings(max_examples=100)
@given(provider=_identifier_st, region=_region_st)
def test_property_12_render_provider_two_space_indent(provider, region):
    """render_provider output uses only two-space indentation."""
    hcl = renderer.render_provider(provider, region)
    _assert_two_space_indentation(hcl)


# --- Imports for Property 10 and 11 ---

from app.generators.api_gateway_generator import APIGatewayGenerator
from app.generators.cloudwatch_generator import CloudWatchGenerator
from app.generators.dynamodb_generator import DynamoDBGenerator
from app.generators.lambda_generator import LambdaGenerator
from app.generators.s3_generator import S3Generator
from app.models.input_models import ServiceType
from app.models.input_models._base import BaseServiceConfig
from app.models.input_models.api_gateway_config import ApiGatewayConfig
from app.models.input_models.cloudwatch_config import CloudWatchConfig
from app.models.input_models.dynamodb_config import DynamoDBConfig
from app.models.input_models.lambda_config import LambdaConfig
from app.models.input_models.s3_config import S3Config
from app.models.ir_models import ResourceInstanceIR

# --- Hypothesis strategies for resource instances ---

_resource_name_st = st.from_regex(r"[a-z][a-z0-9\-]{0,14}", fullmatch=True)

_lambda_config_st = st.builds(
    LambdaConfig,
    handler=st.just("index.handler"),
    runtime=st.sampled_from(["python3.12", "python3.11", "nodejs18.x", "nodejs20.x"]),
    memory_size=st.one_of(st.none(), st.integers(min_value=128, max_value=3008)),
    timeout=st.one_of(st.none(), st.integers(min_value=1, max_value=900)),
    is_layer=st.booleans(),
)

_s3_config_st = st.builds(
    S3Config,
    versioning=st.one_of(st.none(), st.sampled_from(["Enabled", "Suspended"])),
)

_dynamodb_config_st = st.builds(
    DynamoDBConfig,
    billing_mode=st.sampled_from(["PAY_PER_REQUEST", "PROVISIONED"]),
    hash_key=st.from_regex(r"[a-z][a-z0-9_]{0,9}", fullmatch=True),
    hash_key_type=st.sampled_from(["S", "N", "B"]),
    range_key=st.one_of(
        st.none(), st.from_regex(r"[a-z][a-z0-9_]{0,9}", fullmatch=True)
    ),
    range_key_type=st.one_of(st.none(), st.sampled_from(["S", "N", "B"])),
)

_api_gateway_config_st = st.builds(
    ApiGatewayConfig,
    protocol_type=st.sampled_from(["HTTP", "WEBSOCKET"]),
)

_cloudwatch_config_st = st.builds(
    CloudWatchConfig,
    retention_in_days=st.one_of(
        st.none(), st.sampled_from([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365])
    ),
)


def _make_instance(
    name: str, service_type: ServiceType, config: BaseServiceConfig
) -> ResourceInstanceIR:
    return ResourceInstanceIR(name=name, service_type=service_type, config=config)


# --- Property 10: Service-specific required attributes ---
# Feature: terraform-iac-generator, Property 10: Service-specific required attributes
# Validates: Requirements 5.6, 5.7, 5.8, 5.9, 5.10


@settings(max_examples=100)
@given(name=_resource_name_st, config=_lambda_config_st)
def test_property_10_lambda_required_attributes(name, config):
    """Lambda resource block contains function_name, role, handler, runtime."""
    instance = _make_instance(name, ServiceType.LAMBDA, config)
    hcl = LambdaGenerator().generate_resource_tf(instance)
    assert "function_name" in hcl
    assert "role" in hcl
    assert "handler" in hcl
    assert "runtime" in hcl


@settings(max_examples=100)
@given(name=_resource_name_st, config=_s3_config_st)
def test_property_10_s3_required_attributes(name, config):
    """S3 resource block contains bucket attribute."""
    instance = _make_instance(name, ServiceType.S3, config)
    hcl = S3Generator().generate_resource_tf(instance)
    assert "bucket" in hcl


@settings(max_examples=100)
@given(name=_resource_name_st, config=_dynamodb_config_st)
def test_property_10_dynamodb_required_attributes(name, config):
    """DynamoDB resource block contains name, billing_mode, hash_key, and attribute block."""
    instance = _make_instance(name, ServiceType.DYNAMODB, config)
    hcl = DynamoDBGenerator().generate_resource_tf(instance)
    assert "name" in hcl
    assert "billing_mode" in hcl
    assert "hash_key" in hcl
    assert "attribute {" in hcl or "attribute{" in hcl


@settings(max_examples=100)
@given(name=_resource_name_st, config=_api_gateway_config_st)
def test_property_10_api_gateway_required_attributes(name, config):
    """API Gateway resource block contains name and protocol_type."""
    instance = _make_instance(name, ServiceType.API_GATEWAY, config)
    hcl = APIGatewayGenerator().generate_resource_tf(instance)
    assert "name" in hcl
    assert "protocol_type" in hcl


@settings(max_examples=100)
@given(name=_resource_name_st, config=_cloudwatch_config_st)
def test_property_10_cloudwatch_required_attributes(name, config):
    """CloudWatch resource block contains name attribute."""
    instance = _make_instance(name, ServiceType.CLOUDWATCH, config)
    hcl = CloudWatchGenerator().generate_resource_tf(instance)
    assert "name" in hcl


# --- Property 11: HCL block attribute completeness ---
# Feature: terraform-iac-generator, Property 11: HCL block attribute completeness
# Validates: Requirements 5.3, 5.4, 5.5


@settings(max_examples=100)
@given(name=_identifier_st, var_type=_var_type_st, description=_simple_str_st)
def test_property_11_variable_block_completeness(name, var_type, description):
    """Every variable block contains description and type attributes."""
    hcl = renderer.render_variable(name, var_type, description)
    assert "description" in hcl
    assert "type" in hcl


@settings(max_examples=100)
@given(name=_identifier_st, value=_simple_str_st, description=_simple_str_st)
def test_property_11_output_block_completeness(name, value, description):
    """Every output block contains description and value attributes."""
    hcl = renderer.render_output(name, value, description)
    assert "description" in hcl
    assert "value" in hcl


@settings(max_examples=100)
@given(
    name=_identifier_st,
    source=_simple_str_st,
    variables=st.dictionaries(
        keys=_identifier_st, values=_simple_str_st, min_size=0, max_size=5
    ),
)
def test_property_11_module_block_has_source(name, source, variables):
    """Every module block contains a source attribute with a relative path."""
    hcl = renderer.render_module(name, source, variables)
    assert "source" in hcl


# --- Imports for Properties 15–19 ---

import json

from app.generators.iam_policy_generator import IAMPolicyGenerator
from app.models.ir_models import (
    ConnectionIR,
    EnvironmentIR,
    IAMStatement,
    ProjectIR,
    ServiceModuleIR,
)
from app.services.connection_processor import ConnectionProcessor

# --- Hypothesis strategies for connected architectures ---


def _build_project_with_connections(
    lambda_names: list[str],
    target_specs: list[tuple[str, ServiceType, BaseServiceConfig]],
    connections: list[tuple[str, str, str]],
) -> ProjectIR:
    """Build a ProjectIR with Lambda instances, target resources, and connections."""
    lambda_instances = [
        ResourceInstanceIR(
            name=n,
            service_type=ServiceType.LAMBDA,
            config=LambdaConfig(handler="index.handler", runtime="python3.12"),
        )
        for n in lambda_names
    ]

    # Group targets by service type
    from collections import defaultdict

    target_groups: dict[ServiceType, list[ResourceInstanceIR]] = defaultdict(list)
    for tname, tsvc, tcfg in target_specs:
        target_groups[tsvc].append(
            ResourceInstanceIR(name=tname, service_type=tsvc, config=tcfg)
        )

    modules = [
        ServiceModuleIR(service_type=ServiceType.LAMBDA, instances=lambda_instances)
    ]
    for svc, insts in target_groups.items():
        modules.append(ServiceModuleIR(service_type=svc, instances=insts))

    # Build resource lookup for connection validation
    resource_map: dict[str, ServiceType] = {}
    for m in modules:
        for inst in m.instances:
            resource_map[inst.name] = inst.service_type

    conn_irs = [
        ConnectionIR(
            source_name=s,
            target_name=t,
            source_service=resource_map[s],
            target_service=resource_map[t],
            connection_type=ct,
        )
        for s, t, ct in connections
    ]

    return ProjectIR(
        project_name="test-project",
        environments=[
            EnvironmentIR(
                name="dev", variables={}, module_refs=list(resource_map.values())
            )
        ],
        modules=modules,
        connections=conn_irs,
    )


# Strategy: random Lambda name
_lambda_name_st = st.from_regex(r"[a-z][a-z0-9\-]{0,9}", fullmatch=True)

# Strategy: random target service type (things Lambda can connect to)
_target_service_st = st.sampled_from(
    [ServiceType.DYNAMODB, ServiceType.S3, ServiceType.CLOUDWATCH]
)

# Strategy: a Lambda instance IR with random IAM statements
_iam_actions_st = st.lists(
    st.sampled_from(
        [
            "dynamodb:GetItem",
            "dynamodb:PutItem",
            "dynamodb:Query",
            "s3:GetObject",
            "s3:PutObject",
            "s3:DeleteObject",
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutLogEvents",
        ]
    ),
    min_size=1,
    max_size=5,
)

_iam_resource_st = st.from_regex(r"\$\{aws_[a-z_]+\.[a-z0-9\-]+\.arn\}", fullmatch=True)

_iam_statement_st = st.builds(
    IAMStatement,
    effect=st.just("Allow"),
    actions=_iam_actions_st,
    resources=st.lists(_iam_resource_st, min_size=1, max_size=3),
)

_lambda_with_iam_st = st.builds(
    lambda name, stmts: ResourceInstanceIR(
        name=name,
        service_type=ServiceType.LAMBDA,
        config=LambdaConfig(handler="index.handler", runtime="python3.12"),
        iam_statements=stmts,
    ),
    name=_lambda_name_st,
    stmts=st.lists(_iam_statement_st, min_size=0, max_size=4),
)


# --- Property 19: Valid IAM policy JSON syntax ---
# Feature: terraform-iac-generator, Property 19: Valid IAM policy JSON syntax
# Validates: Requirements 9.3

iam_gen = IAMPolicyGenerator()


@settings(max_examples=100)
@given(instance=_lambda_with_iam_st)
def test_property_19_valid_iam_policy_json_syntax(instance):
    """Every generated IAM policy document is valid JSON with required fields."""
    doc_str = iam_gen.generate_policy_document(instance)
    doc = json.loads(doc_str)

    assert doc["Version"] == "2012-10-17"
    assert isinstance(doc["Statement"], list)
    assert len(doc["Statement"]) >= 1  # at least the base execution policy

    for stmt in doc["Statement"]:
        assert "Effect" in stmt
        assert "Action" in stmt
        assert "Resource" in stmt


# --- Property 18: One consolidated IAM policy per Lambda ---
# Feature: terraform-iac-generator, Property 18: One consolidated IAM policy per Lambda
# Validates: Requirements 9.2, 9.6, 9.7


@settings(max_examples=100)
@given(instance=_lambda_with_iam_st)
def test_property_18_one_consolidated_policy_per_lambda(instance):
    """Each Lambda gets exactly one policy document consolidating all statements."""
    doc_str = iam_gen.generate_policy_document(instance)
    doc = json.loads(doc_str)

    # One document produced (single call = single doc)
    assert doc["Version"] == "2012-10-17"

    # Base execution policy is always the first statement
    base_stmt = doc["Statement"][0]
    assert "logs:CreateLogGroup" in base_stmt["Action"]
    assert "logs:CreateLogStream" in base_stmt["Action"]
    assert "logs:PutLogEvents" in base_stmt["Action"]

    # Total statements = 1 (base) + number of connection-derived statements
    expected_count = 1 + len(instance.iam_statements)
    assert len(doc["Statement"]) == expected_count


# --- Property 16: Connection-derived IAM policy statements ---
# Feature: terraform-iac-generator, Property 16: Connection-derived IAM policy statements
# Validates: Requirements 8.2, 8.3, 8.4, 9.4


_dynamodb_target_st = st.builds(
    lambda name: (
        name,
        ServiceType.DYNAMODB,
        DynamoDBConfig(hash_key="id", billing_mode="PAY_PER_REQUEST"),
    ),
    name=st.from_regex(r"[a-z][a-z0-9\-]{0,9}", fullmatch=True),
)

_s3_target_st = st.builds(
    lambda name: (name, ServiceType.S3, S3Config()),
    name=st.from_regex(r"[a-z][a-z0-9\-]{0,9}", fullmatch=True),
)

_cloudwatch_target_st = st.builds(
    lambda name: (name, ServiceType.CLOUDWATCH, CloudWatchConfig()),
    name=st.from_regex(r"[a-z][a-z0-9\-]{0,9}", fullmatch=True),
)


@settings(max_examples=100)
@given(
    lambda_name=_lambda_name_st,
    target=st.one_of(_dynamodb_target_st, _s3_target_st, _cloudwatch_target_st),
)
def test_property_16_connection_derived_iam_statements(lambda_name, target):
    """Lambda connected to DynamoDB/S3/CloudWatch gets scoped IAM statements in its policy."""
    from hypothesis import assume

    tname, tsvc, tcfg = target
    assume(lambda_name != tname)

    project = _build_project_with_connections(
        lambda_names=[lambda_name],
        target_specs=[(tname, tsvc, tcfg)],
        connections=[(lambda_name, tname, "uses")],
    )

    processor = ConnectionProcessor()
    processor.process_all(project)

    # Find the Lambda instance after processing
    lambda_inst = None
    for m in project.modules:
        for inst in m.instances:
            if inst.name == lambda_name:
                lambda_inst = inst
                break

    assert lambda_inst is not None
    assert len(lambda_inst.iam_statements) >= 1

    # Generate the policy and verify connection-derived statements
    doc_str = iam_gen.generate_policy_document(lambda_inst)
    doc = json.loads(doc_str)

    # Should have base + at least one connection-derived statement
    assert len(doc["Statement"]) >= 2

    # Verify the connection-derived statement has actions scoped to the target service
    conn_stmts = doc["Statement"][1:]  # skip base
    if tsvc == ServiceType.DYNAMODB:
        assert any("dynamodb:GetItem" in s["Action"] for s in conn_stmts)
    elif tsvc == ServiceType.S3:
        assert any("s3:GetObject" in s["Action"] for s in conn_stmts)
    elif tsvc == ServiceType.CLOUDWATCH:
        assert any("logs:CreateLogGroup" in s["Action"] for s in conn_stmts)


# --- Property 15: API Gateway–Lambda integration generation ---
# Feature: terraform-iac-generator, Property 15: API Gateway–Lambda integration generation
# Validates: Requirements 8.1


@settings(max_examples=100)
@given(
    apigw_name=st.from_regex(r"[a-z][a-z0-9\-]{0,9}", fullmatch=True),
    lambda_name=_lambda_name_st,
)
def test_property_15_apigw_lambda_integration(apigw_name, lambda_name):
    """API Gateway → Lambda connection generates an aws_apigatewayv2_integration resource."""
    from hypothesis import assume

    assume(apigw_name != lambda_name)

    apigw_inst = ResourceInstanceIR(
        name=apigw_name,
        service_type=ServiceType.API_GATEWAY,
        config=ApiGatewayConfig(protocol_type="HTTP"),
    )
    lambda_inst = ResourceInstanceIR(
        name=lambda_name,
        service_type=ServiceType.LAMBDA,
        config=LambdaConfig(handler="index.handler", runtime="python3.12"),
    )

    conn = ConnectionIR(
        source_name=apigw_name,
        target_name=lambda_name,
        source_service=ServiceType.API_GATEWAY,
        target_service=ServiceType.LAMBDA,
        connection_type="triggers",
    )

    project = ProjectIR(
        project_name="test-project",
        environments=[
            EnvironmentIR(
                name="dev",
                variables={},
                module_refs=[ServiceType.API_GATEWAY, ServiceType.LAMBDA],
            )
        ],
        modules=[
            ServiceModuleIR(
                service_type=ServiceType.API_GATEWAY, instances=[apigw_inst]
            ),
            ServiceModuleIR(service_type=ServiceType.LAMBDA, instances=[lambda_inst]),
        ],
        connections=[conn],
    )

    processor = ConnectionProcessor()
    files = processor.process_all(project)

    assert len(files) >= 1
    integration_files = [
        f for f in files if 'resource "aws_apigatewayv2_integration"' in f.content
    ]
    assert len(integration_files) == 1
    assert lambda_name in integration_files[0].content
    assert apigw_name in integration_files[0].content


# --- Property 17: Terraform references over hardcoded values ---
# Feature: terraform-iac-generator, Property 17: Terraform references over hardcoded values
# Validates: Requirements 8.5


@settings(max_examples=100)
@given(
    apigw_name=st.from_regex(r"[a-z][a-z0-9\-]{0,9}", fullmatch=True),
    lambda_name=_lambda_name_st,
)
def test_property_17_terraform_references_not_hardcoded(apigw_name, lambda_name):
    """Connection-generated HCL uses Terraform resource references, not hardcoded ARNs."""
    from hypothesis import assume

    assume(apigw_name != lambda_name)

    apigw_inst = ResourceInstanceIR(
        name=apigw_name,
        service_type=ServiceType.API_GATEWAY,
        config=ApiGatewayConfig(protocol_type="HTTP"),
    )
    lambda_inst = ResourceInstanceIR(
        name=lambda_name,
        service_type=ServiceType.LAMBDA,
        config=LambdaConfig(handler="index.handler", runtime="python3.12"),
    )

    conn = ConnectionIR(
        source_name=apigw_name,
        target_name=lambda_name,
        source_service=ServiceType.API_GATEWAY,
        target_service=ServiceType.LAMBDA,
        connection_type="triggers",
    )

    project = ProjectIR(
        project_name="test-project",
        environments=[
            EnvironmentIR(
                name="dev",
                variables={},
                module_refs=[ServiceType.API_GATEWAY, ServiceType.LAMBDA],
            )
        ],
        modules=[
            ServiceModuleIR(
                service_type=ServiceType.API_GATEWAY, instances=[apigw_inst]
            ),
            ServiceModuleIR(service_type=ServiceType.LAMBDA, instances=[lambda_inst]),
        ],
        connections=[conn],
    )

    processor = ConnectionProcessor()
    files = processor.process_all(project)

    for f in files:
        content = f.content
        # Should contain Terraform resource references
        assert "aws_apigatewayv2_api." in content or "aws_lambda_function." in content
        # Should NOT contain hardcoded ARN patterns
        assert "arn:aws:lambda:" not in content
        assert "arn:aws:execute-api:" not in content


# --- Imports for Property 3 ---

from app.models.input_models import (
    ArchitectureDescription,
    EnvironmentConfig,
    ResourceInstance,
)
from app.services.code_generator import CodeGenerator
from app.services.ir_builder import IRBuilder

# --- Hypothesis strategies for ArchitectureDescription ---

_project_name_st = st.from_regex(r"[a-z][a-z0-9\-]{2,14}", fullmatch=True)

_env_name_st = st.sampled_from(["dev", "staging", "prod", "qa", "test"])

_env_config_st = st.builds(
    EnvironmentConfig,
    name=_env_name_st,
    variables=st.dictionaries(
        keys=st.from_regex(r"[a-z][a-z0-9_]{0,9}", fullmatch=True),
        values=st.from_regex(r"[a-z0-9\-]{1,10}", fullmatch=True),
        min_size=0,
        max_size=3,
    ),
)

# Per-service resource instance strategies (input model level)
_lambda_resource_st = st.builds(
    ResourceInstance,
    name=_resource_name_st,
    service_type=st.just(ServiceType.LAMBDA),
    config=_lambda_config_st,
)

_s3_resource_st = st.builds(
    ResourceInstance,
    name=_resource_name_st,
    service_type=st.just(ServiceType.S3),
    config=_s3_config_st,
)

_dynamodb_resource_st = st.builds(
    ResourceInstance,
    name=_resource_name_st,
    service_type=st.just(ServiceType.DYNAMODB),
    config=_dynamodb_config_st,
)

_apigw_resource_st = st.builds(
    ResourceInstance,
    name=_resource_name_st,
    service_type=st.just(ServiceType.API_GATEWAY),
    config=_api_gateway_config_st,
)

_cloudwatch_resource_st = st.builds(
    ResourceInstance,
    name=_resource_name_st,
    service_type=st.just(ServiceType.CLOUDWATCH),
    config=_cloudwatch_config_st,
)

_any_resource_st = st.one_of(
    _lambda_resource_st,
    _s3_resource_st,
    _dynamodb_resource_st,
    _apigw_resource_st,
    _cloudwatch_resource_st,
)


@st.composite
def _architecture_description_st(draw):
    """Generate a valid ArchitectureDescription with unique resource/env names."""
    project_name = draw(_project_name_st)

    # Generate 1-3 environments with unique names
    env_names = draw(st.lists(_env_name_st, min_size=1, max_size=3, unique=True))
    environments = [
        draw(
            st.builds(
                EnvironmentConfig,
                name=st.just(name),
                variables=st.dictionaries(
                    keys=st.from_regex(r"[a-z][a-z0-9_]{0,9}", fullmatch=True),
                    values=st.from_regex(r"[a-z0-9\-]{1,10}", fullmatch=True),
                    min_size=0,
                    max_size=3,
                ),
            )
        )
        for name in env_names
    ]

    # Generate 1-5 resources with unique names
    resources = draw(
        st.lists(_any_resource_st, min_size=1, max_size=5).filter(
            lambda rs: len({r.name for r in rs}) == len(rs)
        )
    )

    return ArchitectureDescription(
        project_name=project_name,
        environments=environments,
        resources=resources,
        connections=[],
    )


# --- Property 3: Project-level folder structure ---
# Feature: terraform-iac-generator, Property 3: Project-level folder structure
# Validates: Requirements 2.1, 2.2, 2.3, 3.1, 3.2, 9.1


@settings(max_examples=100)
@given(arch=_architecture_description_st())
def test_property_3_project_level_folder_structure(arch):
    """Generated file tree has correct root, environments, modules, and iam-policies folders."""
    ir_builder = IRBuilder()
    code_gen = CodeGenerator()

    project_ir = ir_builder.build(arch)
    file_tree = code_gen.generate(project_ir)

    root = arch.project_name
    num_envs = len(arch.environments)
    distinct_service_types = {r.service_type for r in arch.resources}
    num_service_types = len(distinct_service_types)

    # All paths should start with the project root name
    for path in file_tree:
        assert path.startswith(f"{root}/"), (
            f"Path {path!r} doesn't start with root {root!r}"
        )

    # Verify environments/ folder has exactly E subfolders
    env_dirs = {
        path.split("/")[2]
        for path in file_tree
        if path.startswith(f"{root}/environments/")
    }
    assert len(env_dirs) == num_envs, (
        f"Expected {num_envs} environment dirs, got {len(env_dirs)}: {env_dirs}"
    )
    for env in arch.environments:
        assert env.name in env_dirs, f"Missing environment dir: {env.name}"

    # Verify modules/ folder contains all distinct service types under their category
    # New structure: {root}/modules/{category}/{service_type}/...
    module_service_types = set()
    for path in file_tree:
        if path.startswith(f"{root}/modules/"):
            parts = path.split("/")
            if len(parts) >= 4:
                module_service_types.add(parts[3])
    assert len(module_service_types) == num_service_types, (
        f"Expected {num_service_types} service type dirs, got {len(module_service_types)}: {module_service_types}"
    )
    for stype in distinct_service_types:
        assert stype.value in module_service_types, (
            f"Missing module dir for service type: {stype.value}"
        )

    # Verify iam-policies/ folder exists (at least as a prefix in some path)
    has_lambda = ServiceType.LAMBDA in distinct_service_types
    iam_policy_paths = [p for p in file_tree if p.startswith(f"{root}/iam-policies/")]
    if has_lambda:
        assert len(iam_policy_paths) >= 1, (
            "iam-policies/ folder should contain policy files for Lambda resources"
        )
    # The iam-policies/ folder should exist conceptually — if there are Lambda resources,
    # there must be policy files; the folder is always part of the structure.


# --- Property 4: Environment file completeness ---
# Feature: terraform-iac-generator, Property 4: Environment file completeness
# Validates: Requirements 2.4

EXPECTED_ENV_FILES = {
    "main.tf",
    "variables.tf",
    "outputs.tf",
    "terraform.tfvars",
    "backend.tf",
    "provider.tf",
    "versions.tf",
}


# --- Property 5: Environment variable consistency ---
# Feature: terraform-iac-generator, Property 5: Environment variable consistency
# Validates: Requirements 2.5, 2.7


def _parse_tfvars(content: str) -> dict[str, str]:
    """Parse terraform.tfvars content into a dict of key -> value."""
    result = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"')
            result[key] = val
    return result


def _parse_variable_names(content: str) -> set[str]:
    """Extract variable names from a variables.tf file."""
    names = set()
    for match in re.finditer(r'variable\s+"([^"]+)"', content):
        names.add(match.group(1))
    return names


@st.composite
def _architecture_with_env_vars_st(draw):
    """Generate a valid ArchitectureDescription where every environment has at least one variable."""
    project_name = draw(_project_name_st)

    env_names = draw(st.lists(_env_name_st, min_size=1, max_size=3, unique=True))

    # Use a shared set of variable keys across environments so we can verify per-env values
    var_keys = draw(
        st.lists(
            st.from_regex(r"[a-z][a-z0-9_]{0,9}", fullmatch=True),
            min_size=1,
            max_size=4,
            unique=True,
        )
    )

    environments = []
    for name in env_names:
        variables = {}
        for k in var_keys:
            variables[k] = draw(st.from_regex(r"[a-z0-9\-]{1,10}", fullmatch=True))
        environments.append(EnvironmentConfig(name=name, variables=variables))

    resources = draw(
        st.lists(_any_resource_st, min_size=1, max_size=3).filter(
            lambda rs: len({r.name for r in rs}) == len(rs)
        )
    )

    return ArchitectureDescription(
        project_name=project_name,
        environments=environments,
        resources=resources,
        connections=[],
    )


@settings(max_examples=100)
@given(arch=_architecture_with_env_vars_st())
def test_property_5_environment_variable_consistency(arch):
    """Variable names in variables.tf match terraform.tfvars keys, and tfvars values match input."""
    ir_builder = IRBuilder()
    code_gen = CodeGenerator()

    project_ir = ir_builder.build(arch)
    file_tree = code_gen.generate(project_ir)

    root = arch.project_name

    for env in arch.environments:
        env_prefix = f"{root}/environments/{env.name}"

        vars_tf_content = file_tree[f"{env_prefix}/variables.tf"]
        tfvars_content = file_tree[f"{env_prefix}/terraform.tfvars"]

        declared_vars = _parse_variable_names(vars_tf_content)
        tfvars_dict = _parse_tfvars(tfvars_content)

        # Every key in terraform.tfvars must be declared in variables.tf
        for key in tfvars_dict:
            assert key in declared_vars, (
                f"Env '{env.name}': tfvars key '{key}' not declared in variables.tf"
            )

        # Every user-defined variable from the input should appear in both files
        for key, value in env.variables.items():
            assert key in declared_vars, (
                f"Env '{env.name}': input variable '{key}' not declared in variables.tf"
            )
            assert key in tfvars_dict, (
                f"Env '{env.name}': input variable '{key}' not in terraform.tfvars"
            )
            assert tfvars_dict[key] == value, (
                f"Env '{env.name}': variable '{key}' has value '{tfvars_dict[key]}', expected '{value}'"
            )

        # The set of tfvars keys should exactly match the user-defined variable keys
        assert set(tfvars_dict.keys()) == set(env.variables.keys()), (
            f"Env '{env.name}': tfvars keys {set(tfvars_dict.keys())} != input keys {set(env.variables.keys())}"
        )


@settings(max_examples=100)
@given(arch=_architecture_description_st())
def test_property_4_environment_file_completeness(arch):
    """Every environment subfolder contains exactly main.tf, variables.tf, outputs.tf, and terraform.tfvars."""
    ir_builder = IRBuilder()
    code_gen = CodeGenerator()

    project_ir = ir_builder.build(arch)
    file_tree = code_gen.generate(project_ir)

    root = arch.project_name

    for env in arch.environments:
        env_prefix = f"{root}/environments/{env.name}/"
        env_files = {
            path.removeprefix(env_prefix)
            for path in file_tree
            if path.startswith(env_prefix)
        }
        assert env_files == EXPECTED_ENV_FILES, (
            f"Environment '{env.name}' has files {env_files}, expected {EXPECTED_ENV_FILES}"
        )


# --- Property 6: Environment module references ---
# Feature: terraform-iac-generator, Property 6: Environment module references
# Validates: Requirements 2.6, 2.8


def _parse_module_names(content: str) -> set[str]:
    """Extract module names from an environment main.tf file."""
    names = set()
    for match in re.finditer(r'module\s+"([^"]+)"', content):
        names.add(match.group(1))
    return names


def _parse_output_names(content: str) -> set[str]:
    """Extract output names from an outputs.tf file."""
    names = set()
    for match in re.finditer(r'output\s+"([^"]+)"', content):
        names.add(match.group(1))
    return names


@settings(max_examples=100)
@given(arch=_architecture_description_st())
def test_property_6_environment_module_references(arch):
    """Environment main.tf has a module block per service type; outputs.tf exposes module outputs."""
    ir_builder = IRBuilder()
    code_gen = CodeGenerator()

    project_ir = ir_builder.build(arch)
    file_tree = code_gen.generate(project_ir)

    root = arch.project_name
    distinct_service_types = {r.service_type for r in arch.resources}

    for env in arch.environments:
        env_prefix = f"{root}/environments/{env.name}"

        # Verify main.tf contains a module block for each distinct service type
        main_tf_content = file_tree[f"{env_prefix}/main.tf"]
        module_names = _parse_module_names(main_tf_content)

        for stype in distinct_service_types:
            assert stype.value in module_names, (
                f"Env '{env.name}': missing module block for service type '{stype.value}' in main.tf"
            )

        # Verify outputs.tf contains output blocks referencing those modules
        outputs_tf_content = file_tree[f"{env_prefix}/outputs.tf"]
        output_names = _parse_output_names(outputs_tf_content)

        for stype in distinct_service_types:
            expected_output = f"{stype.value}_outputs"
            assert expected_output in output_names, (
                f"Env '{env.name}': missing output '{expected_output}' in outputs.tf"
            )

            # Verify the output value references the module
            assert f"module.{stype.value}" in outputs_tf_content, (
                f"Env '{env.name}': output for '{stype.value}' doesn't reference module.{stype.value}"
            )


# --- Property 7: Service module file structure and content ---
# Feature: terraform-iac-generator, Property 7: Service module file structure and content
# Validates: Requirements 3.3, 3.4, 3.5, 3.6

EXPECTED_MODULE_ROOT_FILES = {"main.tf", "variables.tf", "outputs.tf"}


@settings(max_examples=100)
@given(arch=_architecture_description_st())
def test_property_7_service_module_file_structure_and_content(arch):
    """Each service module root has main.tf, variables.tf, outputs.tf with correct content."""
    ir_builder = IRBuilder()
    code_gen = CodeGenerator()

    project_ir = ir_builder.build(arch)
    file_tree = code_gen.generate(project_ir)

    root = arch.project_name

    # Group input resources by service type to know expected instance names
    from collections import defaultdict

    resources_by_type: dict[ServiceType, list[str]] = defaultdict(list)
    for r in arch.resources:
        resources_by_type[r.service_type].append(r.name)

    for stype, instance_names in resources_by_type.items():
        category = get_category(stype)
        mod_base = f"{root}/modules/{category}/{stype.value}"

        # Separate layer instances from regular instances for Lambda
        regular_names = instance_names
        if stype == ServiceType.LAMBDA:
            regular_names = [
                name
                for name, r in zip(
                    instance_names,
                    [res for res in arch.resources if res.service_type == stype],
                )
                if not r.config.is_layer
            ]

        # Req 3.3: module root should contain main.tf, variables.tf, outputs.tf
        root_files = set()
        for path in file_tree:
            if path.startswith(f"{mod_base}/"):
                # Only files directly under mod_base (not in instance subfolders)
                remainder = path.removeprefix(f"{mod_base}/")
                if "/" not in remainder:
                    root_files.add(remainder)

        expected_root_files = set(EXPECTED_MODULE_ROOT_FILES)
        # If there are layer instances, layer.tf should also be at the root
        if stype == ServiceType.LAMBDA:
            has_layers = any(
                r.config.is_layer for r in arch.resources if r.service_type == stype
            )
            if has_layers:
                expected_root_files.add("layer.tf")

        assert expected_root_files.issubset(root_files), (
            f"Module '{stype.value}' root files {root_files} missing expected {expected_root_files - root_files}"
        )

        # Req 3.4: main.tf should have one module block per regular (non-layer) resource instance
        main_tf = file_tree[f"{mod_base}/main.tf"]
        module_names = _parse_module_names(main_tf)
        for inst_name in regular_names:
            assert inst_name in module_names, (
                f"Module '{stype.value}' main.tf missing module block for instance '{inst_name}'"
            )
        assert len(module_names) == len(regular_names), (
            f"Module '{stype.value}' main.tf has {len(module_names)} module blocks, "
            f"expected {len(regular_names)}"
        )

        # Req 3.5: variables.tf exists (already checked above)

        # Req 3.6: outputs.tf should have output blocks aggregating from regular instances
        outputs_tf = file_tree[f"{mod_base}/outputs.tf"]
        output_names = _parse_output_names(outputs_tf)
        for inst_name in regular_names:
            expected_output = f"{inst_name}_outputs"
            assert expected_output in output_names, (
                f"Module '{stype.value}' outputs.tf missing output '{expected_output}'"
            )
            # Verify the output references the instance module
            assert f"module.{inst_name}" in outputs_tf, (
                f"Module '{stype.value}' outputs.tf output for '{inst_name}' "
                f"doesn't reference module.{inst_name}"
            )


# --- Property 8: Resource instance subfolder structure ---
# Feature: terraform-iac-generator, Property 8: Resource instance subfolder structure
# Validates: Requirements 4.1, 4.2, 4.3, 4.4

EXPECTED_INSTANCE_BASE_FILES = {"variables.tf", "outputs.tf"}


@settings(max_examples=100)
@given(arch=_architecture_description_st())
def test_property_8_resource_instance_subfolder_structure(arch):
    """Each resource instance has a named subfolder with {service_type}.tf, variables.tf, outputs.tf."""
    ir_builder = IRBuilder()
    code_gen = CodeGenerator()

    project_ir = ir_builder.build(arch)
    file_tree = code_gen.generate(project_ir)

    root = arch.project_name

    for resource in arch.resources:
        # Lambda layers are aggregated into layer.tf, not individual subfolders
        if resource.service_type == ServiceType.LAMBDA and resource.config.is_layer:
            continue

        stype_name = resource.service_type.value
        category = get_category(resource.service_type)
        inst_base = f"{root}/modules/{category}/{stype_name}/{resource.name}"

        # Req 4.1 & 4.2: a subfolder named after the resource exists
        instance_files = {
            path.removeprefix(f"{inst_base}/")
            for path in file_tree
            if path.startswith(f"{inst_base}/")
            and "/" not in path.removeprefix(f"{inst_base}/")
        }

        # Req 4.3: main resource file named after service type
        resource_tf = f"{stype_name}.tf"
        assert resource_tf in instance_files, (
            f"Resource '{resource.name}' missing {resource_tf} in subfolder"
        )

        # Req 4.4: variables.tf and outputs.tf
        for expected_file in EXPECTED_INSTANCE_BASE_FILES:
            assert expected_file in instance_files, (
                f"Resource '{resource.name}' missing {expected_file} in subfolder"
            )


# --- Property 9: Lambda iam.tf with file() references ---
# Feature: terraform-iac-generator, Property 9: Lambda iam.tf with file() references
# Validates: Requirements 4.5, 4.6, 9.5


@st.composite
def _architecture_with_lambdas_st(draw):
    """Generate a valid ArchitectureDescription that always includes at least one Lambda resource."""
    project_name = draw(_project_name_st)

    env_names = draw(st.lists(_env_name_st, min_size=1, max_size=2, unique=True))
    environments = [EnvironmentConfig(name=name, variables={}) for name in env_names]

    # At least one Lambda (may be a layer)
    lambda_resources = draw(
        st.lists(
            st.builds(
                ResourceInstance,
                name=_resource_name_st,
                service_type=st.just(ServiceType.LAMBDA),
                config=_lambda_config_st,
            ),
            min_size=1,
            max_size=3,
        ).filter(lambda rs: len({r.name for r in rs}) == len(rs))
    )

    # Optionally add non-Lambda resources
    other_resources = draw(
        st.lists(
            st.one_of(
                _s3_resource_st,
                _dynamodb_resource_st,
                _apigw_resource_st,
                _cloudwatch_resource_st,
            ),
            min_size=0,
            max_size=2,
        )
    )

    all_resources = lambda_resources + other_resources
    # Ensure unique names across all resources
    from hypothesis import assume

    assume(len({r.name for r in all_resources}) == len(all_resources))

    return ArchitectureDescription(
        project_name=project_name,
        environments=environments,
        resources=all_resources,
        connections=[],
    )


@settings(max_examples=100)
@given(arch=_architecture_with_lambdas_st())
def test_property_9_lambda_iam_tf_with_file_references(arch):
    """Every Lambda instance (including layers) has iam.tf with file() refs to iam-policies/."""
    ir_builder = IRBuilder()
    code_gen = CodeGenerator()

    project_ir = ir_builder.build(arch)
    file_tree = code_gen.generate(project_ir)

    root = arch.project_name
    lambda_resources = [
        r for r in arch.resources if r.service_type == ServiceType.LAMBDA
    ]

    for resource in lambda_resources:
        # Lambda layers are aggregated into layer.tf, not individual subfolders
        if resource.config.is_layer:
            continue

        inst_base = f"{root}/modules/compute/lambda/{resource.name}"
        iam_tf_path = f"{inst_base}/iam.tf"

        # Req 4.5 / 4.6: iam.tf must exist for every non-layer Lambda
        assert iam_tf_path in file_tree, (
            f"Lambda '{resource.name}' (is_layer={resource.config.is_layer}) missing iam.tf"
        )

        iam_content = file_tree[iam_tf_path]

        # Req 9.5: iam.tf must use file() to reference iam-policies/ folder
        assert "file(" in iam_content, (
            f"Lambda '{resource.name}' iam.tf does not contain file() function call"
        )
        assert "iam-policies/" in iam_content, (
            f"Lambda '{resource.name}' iam.tf does not reference iam-policies/ folder"
        )
        assert f"{resource.name}-policy.json" in iam_content, (
            f"Lambda '{resource.name}' iam.tf does not reference {resource.name}-policy.json"
        )


# --- Property 20: AWS provider configuration ---
# Feature: terraform-iac-generator, Property 20: AWS provider configuration
# Validates: Requirements 5.2


@settings(max_examples=100)
@given(arch=_architecture_description_st())
def test_property_20_aws_provider_configuration(arch):
    """Every environment main.tf contains a provider "aws" block with a configurable region."""
    ir_builder = IRBuilder()
    code_gen = CodeGenerator()

    project_ir = ir_builder.build(arch)
    file_tree = code_gen.generate(project_ir)

    root = arch.project_name

    for env in arch.environments:
        main_tf_path = f"{root}/environments/{env.name}/main.tf"
        assert main_tf_path in file_tree, f"Environment '{env.name}' missing main.tf"

        content = file_tree[main_tf_path]

        # Must contain a provider "aws" block
        assert re.search(r'provider\s+"aws"', content), (
            f"Environment '{env.name}' main.tf missing provider \"aws\" block"
        )

        # The provider block must contain a region attribute
        # Extract the provider block content
        provider_match = re.search(
            r'provider\s+"aws"\s*\{([^}]*)\}', content, re.DOTALL
        )
        assert provider_match, (
            f"Environment '{env.name}' main.tf has malformed provider \"aws\" block"
        )

        provider_body = provider_match.group(1)
        assert "region" in provider_body, (
            f"Environment '{env.name}' provider \"aws\" block missing region attribute"
        )

        # Region should be configurable (reference a variable, not hardcoded)
        assert "var." in provider_body or "local." in provider_body, (
            f"Environment '{env.name}' provider \"aws\" region is not configurable (should use var. or local.)"
        )


# --- Imports for Properties 1, 2, 14 (API endpoint tests) ---

import io
import zipfile

from fastapi.testclient import TestClient

from app.main import app as fastapi_app

_client = TestClient(fastapi_app)


def _arch_to_payload(arch: ArchitectureDescription) -> dict:
    """Convert an ArchitectureDescription to a JSON-serializable dict."""
    return arch.model_dump(mode="json")


# --- Property 1: Valid input acceptance ---
# Feature: terraform-iac-generator, Property 1: Valid input acceptance
# Validates: Requirements 1.1, 1.4


@settings(max_examples=100)
@given(arch=_architecture_description_st())
def test_property_1_valid_input_acceptance(arch):
    """Any valid ArchitectureDescription with supported service types is accepted without errors."""
    payload = _arch_to_payload(arch)
    response = _client.post("/generate/json", json=payload)
    assert response.status_code == 200, (
        f"Valid input rejected with status {response.status_code}: {response.text}"
    )
    body = response.json()
    assert "files" in body
    assert "summary" in body


# --- Property 2: Invalid input error reporting ---
# Feature: terraform-iac-generator, Property 2: Invalid input error reporting
# Validates: Requirements 1.2


@settings(max_examples=100)
@given(arch=_architecture_description_st())
def test_property_2_invalid_input_missing_project_name(arch):
    """Removing project_name from a valid input yields a 422 identifying the missing field."""
    payload = _arch_to_payload(arch)
    del payload["project_name"]
    response = _client.post("/generate/json", json=payload)
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    field_locs = [str(e.get("loc", "")) for e in body["detail"]]
    assert any("project_name" in loc for loc in field_locs)


@settings(max_examples=100)
@given(arch=_architecture_description_st())
def test_property_2_invalid_input_empty_environments(arch):
    """Setting environments to an empty list yields a 422."""
    payload = _arch_to_payload(arch)
    payload["environments"] = []
    response = _client.post("/generate/json", json=payload)
    assert response.status_code == 422


@settings(max_examples=100)
@given(arch=_architecture_description_st())
def test_property_2_invalid_input_empty_resources(arch):
    """Setting resources to an empty list yields a 422."""
    payload = _arch_to_payload(arch)
    payload["resources"] = []
    response = _client.post("/generate/json", json=payload)
    assert response.status_code == 422


# --- Property 14: Output format correctness ---
# Feature: terraform-iac-generator, Property 14: Output format correctness
# Validates: Requirements 6.2, 6.3, 6.4


@settings(max_examples=100)
@given(arch=_architecture_description_st())
def test_property_14_json_output_format(arch):
    """JSON endpoint returns files and summary keys with correct counts."""
    payload = _arch_to_payload(arch)
    response = _client.post("/generate/json", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert "files" in body
    assert "summary" in body

    summary = body["summary"]
    assert summary["project_name"] == arch.project_name
    assert summary["environment_count"] == len(arch.environments)
    assert summary["module_count"] == len({r.service_type for r in arch.resources})
    assert summary["resource_instance_count"] == len(arch.resources)

    # Verify file count is non-zero
    assert len(body["files"]) > 0


# --- Property 13: IR serialization round-trip ---
# Feature: terraform-iac-generator, Property 13: IR serialization round-trip
# Validates: Requirements 7.2, 7.3


from tests.conftest import architecture_description_strategy as _full_arch_st


@settings(max_examples=100)
@given(arch=_full_arch_st())
def test_property_13_ir_serialization_round_trip(arch):
    """Building the IR, serializing it, and deserializing it back produces an equivalent IR.

    Also verifies that the same IR deterministically produces the same file tree,
    confirming no data loss during the generation pipeline for all supported service types.
    """
    ir_builder = IRBuilder()
    code_gen = CodeGenerator()

    # Build IR from input
    project_ir = ir_builder.build(arch)

    # --- Round-trip 1: Pydantic model serialization ---
    # Serialize the IR to a plain dict (JSON-compatible) and reconstruct
    serialized = project_ir.model_dump(mode="json")
    restored_ir = ProjectIR.model_validate(serialized)

    # The restored IR must be structurally equivalent
    assert restored_ir.project_name == project_ir.project_name
    assert len(restored_ir.environments) == len(project_ir.environments)
    assert len(restored_ir.modules) == len(project_ir.modules)
    assert len(restored_ir.connections) == len(project_ir.connections)

    # Deep equality via Pydantic
    assert restored_ir == project_ir

    # --- Round-trip 2: Deterministic file tree generation ---
    # The same IR must produce the exact same file tree (no data loss, no non-determinism)
    file_tree_1 = code_gen.generate(project_ir)

    # Rebuild a fresh IR from the same input to avoid mutation side-effects
    project_ir_2 = ir_builder.build(arch)
    file_tree_2 = code_gen.generate(project_ir_2)

    assert set(file_tree_1.keys()) == set(file_tree_2.keys()), (
        "File tree paths differ between two generations from the same input"
    )
    for path in file_tree_1:
        assert file_tree_1[path] == file_tree_2[path], (
            f"File content differs for '{path}' between two generations"
        )

    # --- Round-trip 3: No data loss for all service types ---
    # Every service type from the input must appear as a module in the IR
    input_service_types = {r.service_type for r in arch.resources}
    ir_service_types = {m.service_type for m in project_ir.modules}
    assert input_service_types == ir_service_types, (
        f"Service types lost in IR: input={input_service_types}, ir={ir_service_types}"
    )

    # Every resource instance from the input must appear in the IR
    input_names = {r.name for r in arch.resources}
    ir_names = {inst.name for m in project_ir.modules for inst in m.instances}
    assert input_names == ir_names, (
        f"Resource instances lost in IR: input={input_names}, ir={ir_names}"
    )

    # Every environment from the input must appear in the IR
    input_envs = {e.name for e in arch.environments}
    ir_envs = {e.name for e in project_ir.environments}
    assert input_envs == ir_envs, (
        f"Environments lost in IR: input={input_envs}, ir={ir_envs}"
    )

    # Every connection from the input must appear in the IR
    assert len(project_ir.connections) == len(arch.connections)


@settings(max_examples=100)
@given(arch=_architecture_description_st())
def test_property_14_zip_output_format(arch):
    """ZIP endpoint returns a valid ZIP archive containing all files from the file tree."""
    payload = _arch_to_payload(arch)

    # Get the JSON response to know expected files
    json_response = _client.post("/generate/json", json=payload)
    assert json_response.status_code == 200
    expected_files = set(json_response.json()["files"].keys())

    # Get the ZIP response
    zip_response = _client.post("/generate/zip", json=payload)
    assert zip_response.status_code == 200
    assert zip_response.headers["content-type"] == "application/zip"

    # Verify it's a valid ZIP
    buf = io.BytesIO(zip_response.content)
    with zipfile.ZipFile(buf, "r") as zf:
        zip_files = set(zf.namelist())
        # ZIP paths have the project_name prefix stripped
        prefix = f"{arch.project_name}/"
        expected_stripped = {p.removeprefix(prefix) for p in expected_files}
        assert zip_files == expected_stripped, (
            f"ZIP files {zip_files} != expected {expected_stripped}"
        )
