"""ConnectionHandler protocol — interface for all connection-type handlers."""

from typing import Protocol

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMGrant,
    IAMStatement,
    ModuleInput,
    ModuleOutput,
    ModuleResource,
    ProjectIR,
    ResourceInstanceIR,
)


def safe_identifier(name: str) -> str:
    """Convert a resource name into a Terraform identifier safe to reference."""
    return name.replace("-", "_")


class ConnectionHandler(Protocol):
    """Protocol that every connection handler must implement."""

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        """Return the module inputs, outputs, resources and IAM this connection adds."""
        ...


class BaseConnectionHandler:
    """Shared helpers for building connection contributions."""

    def __init__(self) -> None:
        self._renderer = HCLRenderer()

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        raise NotImplementedError

    @staticmethod
    def _grant(role_owner: str, statement: IAMStatement) -> IAMGrant:
        return IAMGrant(role_owner=role_owner, statement=statement)

    @staticmethod
    def _output(
        module: str, name: str, value: str, description: str = ""
    ) -> ModuleOutput:
        return ModuleOutput(
            module=module, name=name, value=value, description=description
        )

    @staticmethod
    def _input(
        module: str,
        peer: str,
        suffix: str,
        value: str,
        description: str = "",
    ) -> ModuleInput:
        """Declare a per-peer variable so two connections never collide on one name."""
        return ModuleInput(
            module=module,
            name=f"{safe_identifier(peer)}_{suffix}",
            value=value,
            description=description,
        )

    def _resource(self, module: str, filename: str, content: str) -> ModuleResource:
        return ModuleResource(module=module, filename=filename, content=content)

    @staticmethod
    def _find_instance(name: str, project: ProjectIR) -> ResourceInstanceIR | None:
        """Look up a resource instance by name across all modules."""
        for module in project.modules:
            for inst in module.instances:
                if inst.name == name:
                    return inst
        return None
