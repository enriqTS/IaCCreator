"""Shared fixtures and Hypothesis strategies for Terraform IaC Generator tests."""

from hypothesis import strategies as st

from app.models.input_models import (
    ArchitectureDescription,
    BaseServiceConfig,
    Connection,
    EnvironmentConfig,
    ResourceInstance,
    ServiceType,
)
from app.models.input_models.api_gateway_config import ApiGatewayConfig
from app.models.input_models.cloudwatch_config import CloudWatchConfig
from app.models.input_models.dynamodb_config import DynamoDBConfig
from app.models.input_models.lambda_config import LambdaConfig
from app.models.input_models.s3_config import S3Config

# Compatible connection pairs (must match ir_builder.COMPATIBLE_CONNECTIONS)
COMPATIBLE_CONNECTIONS = {
    (ServiceType.API_GATEWAY, ServiceType.LAMBDA),
    (ServiceType.LAMBDA, ServiceType.DYNAMODB),
    (ServiceType.LAMBDA, ServiceType.S3),
    (ServiceType.LAMBDA, ServiceType.CLOUDWATCH),
}

# ---------------------------------------------------------------------------
# Primitive strategies
# ---------------------------------------------------------------------------

resource_name_st = st.from_regex(r"[a-z][a-z0-9\-]{0,14}", fullmatch=True)

project_name_st = st.from_regex(r"[a-z][a-z0-9\-]{2,14}", fullmatch=True)

env_name_st = st.sampled_from(["dev", "staging", "prod", "qa", "test"])


# ---------------------------------------------------------------------------
# Per-service config strategies (using typed config models)
# ---------------------------------------------------------------------------

lambda_config_st = st.builds(
    LambdaConfig,
    handler=st.just("index.handler"),
    runtime=st.sampled_from(["python3.12", "python3.11", "nodejs18.x", "nodejs20.x"]),
    memory_size=st.one_of(st.none(), st.integers(min_value=128, max_value=3008)),
    timeout=st.one_of(st.none(), st.integers(min_value=1, max_value=900)),
    is_layer=st.booleans(),
)

s3_config_st = st.builds(
    S3Config,
    versioning=st.one_of(st.none(), st.sampled_from(["Enabled", "Suspended"])),
)

dynamodb_config_st = st.builds(
    DynamoDBConfig,
    billing_mode=st.sampled_from(["PAY_PER_REQUEST", "PROVISIONED"]),
    hash_key=st.from_regex(r"[a-z][a-z0-9_]{0,9}", fullmatch=True),
    hash_key_type=st.sampled_from(["S", "N", "B"]),
    range_key=st.one_of(
        st.none(), st.from_regex(r"[a-z][a-z0-9_]{0,9}", fullmatch=True)
    ),
    range_key_type=st.one_of(st.none(), st.sampled_from(["S", "N", "B"])),
)

api_gateway_config_st = st.builds(
    ApiGatewayConfig,
    protocol_type=st.sampled_from(["HTTP", "WEBSOCKET"]),
)

cloudwatch_config_st = st.builds(
    CloudWatchConfig,
    retention_in_days=st.one_of(
        st.none(),
        st.sampled_from([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365]),
    ),
)

# Map ServiceType -> config strategy
_CONFIG_STRATEGIES = {
    ServiceType.LAMBDA: lambda_config_st,
    ServiceType.S3: s3_config_st,
    ServiceType.DYNAMODB: dynamodb_config_st,
    ServiceType.API_GATEWAY: api_gateway_config_st,
    ServiceType.CLOUDWATCH: cloudwatch_config_st,
    ServiceType.IAM: st.builds(BaseServiceConfig),
}


# ---------------------------------------------------------------------------
# resource_instance_strategy(service_type)
# ---------------------------------------------------------------------------


def resource_instance_strategy(
    service_type: ServiceType,
) -> st.SearchStrategy[ResourceInstance]:
    """Generate a random valid ResourceInstance for the given service type."""
    config_st = _CONFIG_STRATEGIES[service_type]
    return st.builds(
        ResourceInstance,
        name=resource_name_st,
        service_type=st.just(service_type),
        config=config_st,
    )


# Convenience: any resource instance across all six service types
any_resource_st = st.one_of(
    resource_instance_strategy(ServiceType.LAMBDA),
    resource_instance_strategy(ServiceType.S3),
    resource_instance_strategy(ServiceType.DYNAMODB),
    resource_instance_strategy(ServiceType.API_GATEWAY),
    resource_instance_strategy(ServiceType.CLOUDWATCH),
    resource_instance_strategy(ServiceType.IAM),
)


# ---------------------------------------------------------------------------
# connection_strategy(resources)
# ---------------------------------------------------------------------------


def connection_strategy(
    resources: list[ResourceInstance],
) -> st.SearchStrategy[list[Connection]]:
    """Generate a list of valid connections between the given resources.

    Only produces connections for compatible (source_service, target_service) pairs
    as defined in COMPATIBLE_CONNECTIONS.
    """
    if not resources:
        return st.just([])

    # Build all valid (source, target) pairs
    valid_pairs: list[tuple[str, str, ServiceType, ServiceType]] = []
    for src in resources:
        for tgt in resources:
            if src.name == tgt.name:
                continue
            if (src.service_type, tgt.service_type) in COMPATIBLE_CONNECTIONS:
                valid_pairs.append(
                    (src.name, tgt.name, src.service_type, tgt.service_type)
                )

    if not valid_pairs:
        return st.just([])

    connection_type_map = {
        (ServiceType.API_GATEWAY, ServiceType.LAMBDA): "triggers",
        (ServiceType.LAMBDA, ServiceType.DYNAMODB): "reads_from",
        (ServiceType.LAMBDA, ServiceType.S3): "writes_to",
        (ServiceType.LAMBDA, ServiceType.CLOUDWATCH): "logs_to",
    }

    pair_st = st.sampled_from(valid_pairs)

    @st.composite
    def _build_connections(draw):
        n = draw(st.integers(min_value=0, max_value=min(len(valid_pairs), 4)))
        chosen = draw(
            st.lists(pair_st, min_size=n, max_size=n).filter(
                lambda cs: len({(c[0], c[1]) for c in cs}) == len(cs)
            )
        )
        return [
            Connection(
                source=src,
                target=tgt,
                connection_type=connection_type_map.get((src_svc, tgt_svc), "uses"),
            )
            for src, tgt, src_svc, tgt_svc in chosen
        ]

    return _build_connections()


# ---------------------------------------------------------------------------
# architecture_description_strategy()
# ---------------------------------------------------------------------------


@st.composite
def architecture_description_strategy(draw):
    """Generate a random valid ArchitectureDescription covering all six service types.

    Produces unique resource names, unique environment names, and only
    compatible connections between existing resources.
    """
    project_name = draw(project_name_st)

    # 1-3 environments with unique names
    env_names = draw(st.lists(env_name_st, min_size=1, max_size=3, unique=True))
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

    # 1-6 resources with unique names, covering a random subset of service types
    resources = draw(
        st.lists(any_resource_st, min_size=1, max_size=6).filter(
            lambda rs: len({r.name for r in rs}) == len(rs)
        )
    )

    # Generate valid connections between the drawn resources
    connections = draw(connection_strategy(resources))

    return ArchitectureDescription(
        project_name=project_name,
        environments=environments,
        resources=resources,
        connections=connections,
    )
