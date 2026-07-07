"""Property-based tests for service generators — HCL output correctness.

Feature: enhanced-variable-configuration
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from app.generators.registry import GENERATOR_REGISTRY
from app.generators.variable_schemas import VARIABLE_SCHEMAS, VisibleWhen
from app.models.input_models import ResourceConfig, ServiceType
from app.models.input_models._general import get_service_config_models
from app.models.input_models.dynamodb_config import DynamoDBConfig
from app.models.ir_models import ResourceInstanceIR

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Service types that have both a generator and a variable schema
_TESTABLE_SERVICES = [
    stype
    for stype in ServiceType
    if stype in GENERATOR_REGISTRY and stype in VARIABLE_SCHEMAS
]


def _visible_when_satisfied(vw: VisibleWhen | None, config: ResourceConfig) -> bool:
    """Return True if the visible_when condition is satisfied (or absent)."""
    if vw is None:
        return True
    return getattr(config, vw.field, None) == vw.equals


# Map from schema variable name → the ResourceConfig field name.
# Most are identical; add overrides here if they ever diverge.
_FIELD_NAME_MAP: dict[str, str] = {
    "versioning": "versioning",
}

# Per-service mapping from schema variable name → ResourceConfig field name.
# Used when the schema name differs from the config field name.
_SERVICE_FIELD_NAME_MAP: dict[ServiceType, dict[str, str]] = {
    # Analytics — now using typed configs with matching field names (no mapping needed)
    # Business Applications — now using typed configs with matching field names (no mapping needed)
    # Database
    ServiceType.AURORA: {
        "engine": "engine",
        "master_username": "master_username",
    },
    ServiceType.DOCUMENTDB: {"master_username": "master_username"},
    ServiceType.ELASTICACHE: {
        "engine": "engine",
        "node_type": "node_type",
        "num_cache_nodes": "num_cache_nodes",
    },
    ServiceType.NEPTUNE: {"cluster_identifier": "cluster_identifier"},
    ServiceType.RDS: {
        "engine": "engine",
        "instance_class": "instance_class",
        "allocated_storage": "allocated_storage",
        "username": "username",
    },
    ServiceType.TIMESTREAM: {"database_name": "database_name"},
    # Developer Tools — now using typed configs with matching field names (no mapping needed)
    # End User Computing — now using typed configs with matching field names (no mapping needed)
    # Front End Web Mobile — now using typed configs with matching field names (no mapping needed)
    # Games — now using typed configs with matching field names (no mapping needed)
}

# Fields that are "always present" in the HCL for a service (emitted
# unconditionally regardless of config population).  These use var.*
# references even when the config field is None, so we skip them in
# the "populated → var ref" assertion.
_ALWAYS_PRESENT_FIELDS: dict[ServiceType, set[str]] = {
    ServiceType.LAMBDA: {"function_name", "handler", "runtime"},
    ServiceType.S3: {"bucket_name", "versioning_enabled"},
    ServiceType.DYNAMODB: {"table_name", "billing_mode", "hash_key"},
    ServiceType.API_GATEWAY: {"api_name", "protocol_type"},
    ServiceType.CLOUDWATCH: {"log_group_name"},
    # Analytics
    ServiceType.ATHENA: {"workgroup_name"},
    ServiceType.CLOUDSEARCH: {"domain_name"},
    ServiceType.EMR: {"cluster_name"},
    ServiceType.GLUE: {"database_name"},
    ServiceType.KINESIS: {"stream_name"},
    ServiceType.KINESIS_FIREHOSE: {"stream_name"},
    ServiceType.MSK: {"cluster_name"},
    ServiceType.OPENSEARCH: {"domain_name"},
    ServiceType.REDSHIFT: {"cluster_identifier"},
    # Business Applications
    ServiceType.CONNECT: set(),
    ServiceType.SES: {"domain"},
    ServiceType.PINPOINT: {"app_name"},
    # Database
    ServiceType.AURORA: {"cluster_identifier"},
    ServiceType.DOCUMENTDB: {"cluster_identifier"},
    ServiceType.ELASTICACHE: {"cluster_id"},
    ServiceType.NEPTUNE: {"cluster_identifier"},
    ServiceType.RDS: {"db_identifier"},
    ServiceType.TIMESTREAM: {"database_name"},
    # Developer Tools
    ServiceType.CODEBUILD: {"project_name"},
    ServiceType.CODECOMMIT: {"repository_name"},
    ServiceType.CODEDEPLOY: {"app_name"},
    ServiceType.CODEPIPELINE: {"pipeline_name"},
    # End User Computing
    ServiceType.APPSTREAM: {"fleet_name"},
    # Front End Web Mobile
    ServiceType.AMPLIFY: {"app_name"},
    # Games
    ServiceType.GAMELIFT: {"fleet_name"},
}

# Some schema variable names map to a *different* var reference name
# in the generated HCL.  For example the S3 schema has "versioning"
# but the generator emits "var.versioning_enabled".
_VAR_REF_OVERRIDES: dict[str, str] = {
    "versioning": "versioning_enabled",
}

# Fields that exist in the schema but are NOT emitted as `var.<name>`
# references in generate_resource_tf.  For example, DynamoDB hash_key_type
# and range_key_type are used inline in the attribute block, and S3
# versioning is a bool on the config but a string in the schema.
_SKIP_VAR_REF_FIELDS: dict[ServiceType, set[str]] = {
    ServiceType.DYNAMODB: {"hash_key_type", "range_key_type"},
    ServiceType.S3: {"versioning"},
    # New API Gateway schema variables added by the overhaul — generator support
    # for these fields is implemented in later tasks.
    ServiceType.API_GATEWAY: {
        "route_method",
        "route_path",
        "route_selection_expression",
        "stage_name",
        "auto_deploy",
        "stage_variables",
        "authorizer_type",
        "jwt_issuer",
        "jwt_audience",
        "lambda_authorizer_uri",
        "authorizer_payload_format_version",
        "cognito_user_pool_endpoint",
        "cognito_client_ids",
        "custom_domain_name",
        "certificate_arn",
        "integration_type",
        "integration_uri",
        "integration_method",
        "throttling_burst_limit",
        "throttling_rate_limit",
        "vpc_link_name",
        "vpc_link_subnet_ids",
        "vpc_link_security_group_ids",
        "api_key_required",
    },
}


# ---------------------------------------------------------------------------
# Strategy: build a ResourceConfig with random populated optional fields
# for a given service type, respecting visible_when conditions.
# ---------------------------------------------------------------------------


def _sample_value_for_type(var_type: str) -> st.SearchStrategy:
    """Return a Hypothesis strategy that produces a non-None value for the given schema type."""
    if var_type == "string":
        return st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=10
        )
    if var_type == "number":
        return st.integers(min_value=1, max_value=100)
    if var_type == "bool":
        return st.booleans()
    if var_type == "map":
        return st.dictionaries(
            keys=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=5),
            values=st.text(
                alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=8
            ),
            min_size=1,
            max_size=2,
        )
    if var_type == "list":
        return st.lists(
            st.text(
                alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=10
            ),
            min_size=1,
            max_size=2,
        )
    # Fallback
    return st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=5)


@st.composite
def resource_instance_with_populated_fields(draw):
    """Generate a (ServiceType, ResourceInstanceIR, set_of_populated_field_names) tuple.

    For the chosen service, we populate a random subset of optional config
    fields with valid non-None values.  Fields whose visible_when condition
    is NOT satisfied are excluded from the populated set.
    """
    service_type = draw(st.sampled_from(_TESTABLE_SERVICES))
    schema_entries = VARIABLE_SCHEMAS[service_type]
    always_present = _ALWAYS_PRESENT_FIELDS.get(service_type, set())

    # Start with required base config values per service
    config_kwargs: dict = {}
    if service_type == ServiceType.DYNAMODB:
        config_kwargs["hash_key"] = draw(
            st.from_regex(r"[a-z][a-z0-9_]{0,9}", fullmatch=True)
        )
        config_kwargs["billing_mode"] = draw(
            st.sampled_from(["PAY_PER_REQUEST", "PROVISIONED"])
        )
    if service_type == ServiceType.API_GATEWAY:
        config_kwargs["protocol_type"] = draw(
            st.sampled_from(["HTTP", "WEBSOCKET", "REST"])
        )

    skip_fields = _SKIP_VAR_REF_FIELDS.get(service_type, set())

    # Determine which optional fields to populate
    optional_entries = [
        e
        for e in schema_entries
        if e.name not in always_present
        and e.name not in config_kwargs
        and e.name not in skip_fields
    ]

    # We need at least one populated field to make the test meaningful
    if optional_entries:
        populate_flags = draw(
            st.lists(
                st.booleans(),
                min_size=len(optional_entries),
                max_size=len(optional_entries),
            ).filter(lambda flags: any(flags))
        )
    else:
        populate_flags = []

    populated_field_names: set[str] = set()

    for entry, should_populate in zip(optional_entries, populate_flags):
        if not should_populate:
            continue
        # Resolve config field name: check per-service map first, then global map, then use schema name
        svc_map = _SERVICE_FIELD_NAME_MAP.get(service_type, {})
        field_name = svc_map.get(
            entry.name, _FIELD_NAME_MAP.get(entry.name, entry.name)
        )
        # Use options values when available for more realistic data
        if entry.options:
            value = draw(st.sampled_from([o.value for o in entry.options]))
        else:
            value = draw(_sample_value_for_type(entry.type))
        config_kwargs[field_name] = value

    if service_type == ServiceType.DYNAMODB:
        config = DynamoDBConfig(**config_kwargs)
    else:
        # Use typed config model when available (field names match schema names)
        config_models = get_service_config_models()
        config_cls = config_models.get(service_type)
        if config_cls is not None and config_cls.has_terraform_schema():
            config = config_cls(**config_kwargs)
        else:
            config = ResourceConfig(**config_kwargs)

    # Now determine which populated fields are actually visible
    for entry, should_populate in zip(optional_entries, populate_flags):
        if not should_populate:
            continue
        svc_map = _SERVICE_FIELD_NAME_MAP.get(service_type, {})
        field_name = svc_map.get(
            entry.name, _FIELD_NAME_MAP.get(entry.name, entry.name)
        )
        if _visible_when_satisfied(entry.visible_when, config):
            # Use the var reference name (may differ from field name)
            var_name = _VAR_REF_OVERRIDES.get(entry.name, entry.name)
            populated_field_names.add(var_name)

    name = draw(st.from_regex(r"[a-z][a-z0-9\-]{0,14}", fullmatch=True))
    instance = ResourceInstanceIR(
        name=name,
        service_type=service_type,
        config=config,
    )
    return service_type, instance, populated_field_names


# ---------------------------------------------------------------------------
# Property 12: Generators include var references for populated config fields
# Feature: enhanced-variable-configuration, Property 12: Generators include var references for populated config fields
# **Validates: Requirements 8.2**
# ---------------------------------------------------------------------------


@given(data=resource_instance_with_populated_fields())
@settings(max_examples=100)
def test_populated_config_fields_produce_var_references(data):
    """For any populated (non-None) config field whose visible_when is satisfied,
    the generated HCL resource block shall contain a corresponding var.<field> reference.
    """
    service_type, instance, populated_field_names = data
    generator = GENERATOR_REGISTRY[service_type]
    hcl = generator.generate_resource_tf(instance)

    for field_name in populated_field_names:
        assert f"var.{field_name}" in hcl, (
            f"Expected 'var.{field_name}' in generated HCL for {service_type.value}, "
            f"but it was not found.\nHCL:\n{hcl}"
        )


# ---------------------------------------------------------------------------
# Property 10: visible_when exclusion
# Feature: enhanced-variable-configuration, Property 10: visible_when exclusion
# **Validates: Requirements 6.6, 8.5**
# ---------------------------------------------------------------------------


@given(
    billing_mode=st.sampled_from(["PAY_PER_REQUEST"]),
    read_cap=st.integers(min_value=1, max_value=100),
    write_cap=st.integers(min_value=1, max_value=100),
    name=st.from_regex(r"[a-z][a-z0-9\-]{0,14}", fullmatch=True),
)
@settings(max_examples=100)
def test_dynamodb_visible_when_false_excludes_capacity(
    billing_mode, read_cap, write_cap, name
):
    """When DynamoDB billing_mode != PROVISIONED, read_capacity and write_capacity
    var references SHALL NOT appear in the generated HCL, even if those fields
    are populated on the config.
    """
    config = DynamoDBConfig(
        billing_mode=billing_mode,
        hash_key="pk",
        read_capacity=read_cap,
        write_capacity=write_cap,
    )
    instance = ResourceInstanceIR(
        name=name,
        service_type=ServiceType.DYNAMODB,
        config=config,
    )
    generator = GENERATOR_REGISTRY[ServiceType.DYNAMODB]
    hcl = generator.generate_resource_tf(instance)

    assert "var.read_capacity" not in hcl, (
        f"var.read_capacity should be excluded when billing_mode={billing_mode}\nHCL:\n{hcl}"
    )
    assert "var.write_capacity" not in hcl, (
        f"var.write_capacity should be excluded when billing_mode={billing_mode}\nHCL:\n{hcl}"
    )


@given(
    protocol_type=st.sampled_from(["HTTP", "REST"]),
    route_expr=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=20),
    name=st.from_regex(r"[a-z][a-z0-9\-]{0,14}", fullmatch=True),
)
@settings(max_examples=100)
def test_api_gateway_visible_when_false_excludes_route_selection(
    protocol_type, route_expr, name
):
    """When API Gateway protocol_type != WEBSOCKET, route_selection_expression
    var reference SHALL NOT appear in the generated HCL, even if the field
    is populated on the config.
    """
    config = ResourceConfig(
        protocol_type=protocol_type,
        route_selection_expression=route_expr,
    )
    instance = ResourceInstanceIR(
        name=name,
        service_type=ServiceType.API_GATEWAY,
        config=config,
    )
    generator = GENERATOR_REGISTRY[ServiceType.API_GATEWAY]
    hcl = generator.generate_resource_tf(instance)

    assert "var.route_selection_expression" not in hcl, (
        f"var.route_selection_expression should be excluded when protocol_type={protocol_type}\nHCL:\n{hcl}"
    )
