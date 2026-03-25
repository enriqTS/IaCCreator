"""Internal Representation (IR) data models for the Terraform IaC Generator."""

from pydantic import BaseModel, Field

from app.models.input_models import ResourceConfig, ServiceType

# Central output type: maps relative file paths to file contents
FileTree = dict[str, str]


class IAMStatement(BaseModel):
    """A single IAM policy statement."""

    effect: str = "Allow"
    actions: list[str]
    resources: list[str]  # Terraform references, e.g., "${aws_dynamodb_table.my_table.arn}"


class ConnectionIR(BaseModel):
    """A normalized connection between two resource instances in the IR."""

    source_name: str
    target_name: str
    source_service: ServiceType
    target_service: ServiceType
    connection_type: str


class ResourceInstanceIR(BaseModel):
    """A resource instance in the IR, enriched with IAM and connection data."""

    name: str
    service_type: ServiceType
    config: ResourceConfig
    iam_statements: list[IAMStatement] = Field(default_factory=list)
    connections: list[ConnectionIR] = Field(default_factory=list)


class ServiceModuleIR(BaseModel):
    """A service module grouping all instances of a single service type."""

    service_type: ServiceType
    instances: list[ResourceInstanceIR]


class EnvironmentIR(BaseModel):
    """An environment in the IR with variable bindings and module references."""

    name: str
    variables: dict[str, str]
    module_refs: list[ServiceType]  # Which modules this environment references


class ProjectIR(BaseModel):
    """Top-level IR representing the entire Terraform project."""

    project_name: str
    environments: list[EnvironmentIR]
    modules: list[ServiceModuleIR]
    connections: list[ConnectionIR]


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
