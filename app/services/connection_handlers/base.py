"""ConnectionHandler protocol — interface for all connection-type handlers."""

from typing import Protocol

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import (
    ConnectionIR,
    GeneratedFile,
    IAMStatement,
    ProjectIR,
    ResourceInstanceIR,
)


class ConnectionHandler(Protocol):
    """Protocol that every connection handler must implement."""

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """Process a connection and return any generated HCL files.

        IAM statements should be attached in-place to the relevant
        ResourceInstanceIR via the helper methods in BaseConnectionHandler.
        """
        ...


class BaseConnectionHandler:
    """Shared utilities for connection handlers.

    Provides HCL renderer access, IAM statement attachment, and instance lookup.
    Concrete handlers should inherit from this class.
    """

    def __init__(self) -> None:
        self._renderer = HCLRenderer()

    def handle(self, connection: ConnectionIR, project: ProjectIR) -> list[GeneratedFile]:
        raise NotImplementedError

    def _attach_iam_statement(
        self, lambda_name: str, statement: IAMStatement, project: ProjectIR
    ) -> None:
        """Find the Lambda ResourceInstanceIR in the project and append the IAM statement."""
        instance = self._find_instance(lambda_name, project)
        if instance is not None:
            instance.iam_statements.append(statement)

    @staticmethod
    def _find_instance(name: str, project: ProjectIR) -> ResourceInstanceIR | None:
        """Look up a resource instance by name across all modules."""
        for module in project.modules:
            for inst in module.instances:
                if inst.name == name:
                    return inst
        return None
