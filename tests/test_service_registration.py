"""Registration invariants tying ServiceType to the generator, schema and category tables."""

from app.generators.registry import GENERATOR_REGISTRY
from app.generators.service_category_map import get_category
from app.models.input_models import ServiceType
from app.models.input_models._base import BaseServiceConfig
from app.models.ir_models import (
    EnvironmentIR,
    GlobalTerraformConfigIR,
    ProjectIR,
    ResourceInstanceIR,
    ServiceModuleIR,
)
from app.services.file_tree_assembler import FileTreeAssembler
from tests.generator_helpers import minimal_config_for
from tests.schema_helpers import service_schemas

# IAM modules are emitted by connection handlers, so IAM has no user-facing schema
SCHEMALESS_GENERATORS = {ServiceType.IAM}

ICON_ONLY_SERVICES = [s for s in ServiceType if s not in GENERATOR_REGISTRY]


def _project(modules: list[ServiceModuleIR]) -> ProjectIR:
    return ProjectIR(
        project_name="registration-test",
        environments=[EnvironmentIR(name="dev", variables={}, module_refs=[])],
        modules=modules,
        connections=[],
        global_config=GlobalTerraformConfigIR(),
    )


def test_enum_values_are_kebab_case_member_names() -> None:
    """The frontend maps icons by enum value, so a hand-typed value silently breaks one."""
    mismatched = [
        f"{s.name} -> {s.value}"
        for s in ServiceType
        if s.value != s.name.lower().replace("_", "-")
    ]
    assert not mismatched, "ServiceType values off convention:\n" + "\n".join(
        mismatched
    )


def test_generator_backed_services_have_a_schema() -> None:
    """A generator with no schema gives the editor nothing to render for the service."""
    schemas = service_schemas()
    missing = [
        s.value
        for s in GENERATOR_REGISTRY
        if s not in SCHEMALESS_GENERATORS and not schemas.get(s)
    ]
    assert not missing, f"Generator-backed services without a schema: {missing}"


def test_only_generator_backed_services_have_a_schema() -> None:
    """A schema for a service that cannot generate offers configuration that goes nowhere."""
    schemas = service_schemas()
    orphans = [
        s.value for s in ServiceType if s not in GENERATOR_REGISTRY and schemas.get(s)
    ]
    assert not orphans, f"Icon-only services carrying a schema: {orphans}"


def test_generator_backed_services_have_a_category() -> None:
    """The category decides the module directory, so a missing one misplaces the module."""
    uncategorized = [s.value for s in GENERATOR_REGISTRY if not get_category(s)]
    assert not uncategorized, (
        f"Generator-backed services without a category: {uncategorized}"
    )


def test_assembler_emits_no_files_for_icon_only_services() -> None:
    """Icon-only services are diagram decoration; emitting a module would break init."""
    modules = [
        ServiceModuleIR(
            service_type=s,
            instances=[
                ResourceInstanceIR(
                    name=f"{s.value}-node",
                    service_type=s,
                    config=BaseServiceConfig(),
                )
            ],
        )
        for s in ICON_ONLY_SERVICES
    ]
    tree = FileTreeAssembler().assemble(_project(modules))
    leaked = [p for p in tree if "/modules/" in p]
    assert not leaked, f"Icon-only services produced module files: {leaked[:10]}"


def test_assembler_emits_files_for_generator_backed_services() -> None:
    """Every registered generator must actually reach the tree, not just exist."""
    silent = []
    for service_type in GENERATOR_REGISTRY:
        if service_type in SCHEMALESS_GENERATORS:
            continue
        module = ServiceModuleIR(
            service_type=service_type,
            instances=[
                ResourceInstanceIR(
                    name="probe",
                    service_type=service_type,
                    config=minimal_config_for(service_type),
                )
            ],
        )
        tree = FileTreeAssembler().assemble(_project([module]))
        if not [p for p in tree if "/modules/" in p]:
            silent.append(service_type.value)
    assert not silent, f"Registered generators producing no module files: {silent}"
