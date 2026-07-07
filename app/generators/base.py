"""ServiceGenerator protocol — interface for all service-specific generators."""

from typing import Protocol, TypeVar

from app.exceptions import GeneratorConfigError
from app.models.input_models._base import BaseServiceConfig
from app.models.ir_models import ResourceInstanceIR

T = TypeVar("T", bound=BaseServiceConfig)


def get_typed_config(instance: ResourceInstanceIR, expected: type[T]) -> T:
    """Cast instance.config to the expected typed config.

    Raises GeneratorConfigError if the config is not an instance of the expected class.
    """
    if isinstance(instance.config, expected):
        return instance.config
    raise GeneratorConfigError(
        f"Expected {expected.__name__} for service {instance.service_type.value}, "
        f"got {type(instance.config).__name__} for instance '{instance.name}'"
    )


class ServiceGenerator(Protocol):
    """Protocol that every AWS service generator must implement."""

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str: ...

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str: ...

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str: ...
