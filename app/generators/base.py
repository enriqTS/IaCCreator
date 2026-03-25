"""ServiceGenerator protocol — interface for all service-specific generators."""

from typing import Protocol

from app.models.ir_models import ResourceInstanceIR


class ServiceGenerator(Protocol):
    """Protocol that every AWS service generator must implement."""

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str: ...

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str: ...

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str: ...
