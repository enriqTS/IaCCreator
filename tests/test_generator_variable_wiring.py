"""Universal wiring invariants every service generator must satisfy."""

from app.generators.registry import GENERATOR_REGISTRY
from app.models.input_models import ServiceType
from app.models.input_models._general import get_service_config_models
from tests.generator_helpers import (
    VAR_REFERENCE,
    VARIABLE_DECLARATION,
    generated_files,
)

# Fields the generator consumes inline rather than through a var reference
INLINE_ONLY_FIELDS: dict[ServiceType, set[str]] = {
    ServiceType.DYNAMODB: {"hash_key_type"},
}


def test_required_config_fields_are_wired_as_variables() -> None:
    """A required field the resource never references means the value silently vanishes."""
    models = get_service_config_models()
    failures = []
    for service_type in GENERATOR_REGISTRY:
        config_cls = models.get(service_type)
        if config_cls is None or not config_cls.has_terraform_schema():
            continue
        inline = INLINE_ONLY_FIELDS.get(service_type, set())
        required = [
            name
            for name, field in config_cls.model_fields.items()
            if field.is_required() and name not in inline
        ]
        if not required:
            continue
        referenced = set(
            VAR_REFERENCE.findall(generated_files(service_type)["resource"])
        )
        missing = sorted(set(required) - referenced)
        if missing:
            failures.append(f"{service_type.value}: {missing}")

    assert not failures, (
        "Required fields never referenced in resource_tf:\n" + "\n".join(failures)
    )


def test_no_undeclared_variable_references() -> None:
    """A var reference with no matching variable block is Terraform that cannot init."""
    failures = []
    for service_type in GENERATOR_REGISTRY:
        files = generated_files(service_type)
        declared = set(VARIABLE_DECLARATION.findall(files["variables"]))
        referenced = set(VAR_REFERENCE.findall(files["resource"])) | set(
            VAR_REFERENCE.findall(files["outputs"])
        )
        undeclared = sorted(referenced - declared)
        if undeclared:
            failures.append(f"{service_type.value}: {undeclared}")

    assert not failures, "Undeclared var references:\n" + "\n".join(failures)
