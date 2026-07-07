"""Internal Representation (IR) data models for the Terraform IaC Generator."""

from pydantic import BaseModel, Field, SerializeAsAny, model_validator

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType

# Central output type: maps relative file paths to file contents
FileTree = dict[str, str]


class IAMStatement(BaseModel):
    """A single IAM policy statement."""

    effect: str = "Allow"
    actions: list[str]
    resources: list[
        str
    ]  # Terraform references, e.g., "${aws_dynamodb_table.my_table.arn}"


class ConnectionIR(BaseModel):
    """A normalized connection between two resource instances in the IR."""

    source_name: str
    target_name: str
    source_service: ServiceType
    target_service: ServiceType
    connection_type: str
    connection_config: dict[str, str | int | float | bool] = Field(default_factory=dict)


class ResourceInstanceIR(BaseModel):
    """A resource instance in the IR, enriched with IAM and connection data."""

    name: str
    service_type: ServiceType
    config: SerializeAsAny[BaseServiceConfig]
    iam_statements: list[IAMStatement] = Field(default_factory=list)
    connections: list[ConnectionIR] = Field(default_factory=list)
    terraform_variables: dict[str, str | int | float | bool] = Field(
        default_factory=dict
    )

    @model_validator(mode="before")
    @classmethod
    def resolve_typed_config(cls, data: dict) -> dict:
        """Resolve config to the typed model based on service_type during deserialization.

        When config is provided as a plain dict (e.g. from model_validate after
        model_dump), coerce it into the appropriate typed config model using the
        SERVICE_CONFIG_MODELS registry. This ensures round-trip serialization
        preserves the concrete config subclass.
        """
        if not isinstance(data, dict):
            return data
        config = data.get("config")
        service_type = data.get("service_type")
        if config is None or service_type is None:
            return data
        # If config is already a BaseServiceConfig instance, keep it
        if isinstance(config, BaseServiceConfig):
            return data
        # If config is a dict, resolve to typed model
        if isinstance(config, dict):
            from app.models.input_models._general import _get_cached_service_config_models

            registry = _get_cached_service_config_models()
            stype = ServiceType(service_type) if isinstance(service_type, str) else service_type
            config_cls = registry.get(stype)
            if config_cls is not None:
                data["config"] = config_cls.model_validate(config)
            else:
                data["config"] = BaseServiceConfig.model_validate(config)
        return data


class ServiceModuleIR(BaseModel):
    """A service module grouping all instances of a single service type."""

    service_type: ServiceType
    instances: list[ResourceInstanceIR]


class EnvironmentIR(BaseModel):
    """An environment in the IR with variable bindings and module references."""

    name: str
    variables: dict[str, str]
    module_refs: list[ServiceType]  # Which modules this environment references


class GlobalTerraformConfigIR(BaseModel):
    """Project-level Terraform configuration in the IR."""

    backend_type: str = "local"
    backend_config: dict[str, str] = Field(default_factory=dict)
    provider_region: str = "us-east-1"
    provider_profile: str | None = None
    terraform_version: str | None = None
    aws_provider_version: str | None = None


class ProjectIR(BaseModel):
    """Top-level IR representing the entire Terraform project."""

    project_name: str
    environments: list[EnvironmentIR]
    modules: list[ServiceModuleIR]
    connections: list[ConnectionIR]
    global_config: GlobalTerraformConfigIR = Field(
        default_factory=GlobalTerraformConfigIR
    )


class GeneratedFile(BaseModel):
    """A single generated file with its path and content."""

    path: str  # Relative path from project root
    content: str  # File content (HCL or JSON)


class GenerationSummary(BaseModel):
    """Summary statistics for a generation run."""

    project_name: str
    environment_count: int
    module_count: int
    resource_instance_count: int
    iam_policy_count: int
