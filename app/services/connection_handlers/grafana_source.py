"""Data-source implementations contribute independently to one workspace role."""

from dataclasses import dataclass, field
from typing import Protocol

from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import ConnectionContribution, ProjectIR


@dataclass
class GrafanaSourceContribution:
    contribution: ConnectionContribution = field(default_factory=ConnectionContribution)
    statements: list[dict | Expr] = field(default_factory=list)
    preconditions: list[dict] = field(default_factory=list)
    issues: list[ConnectionIssue] = field(default_factory=list)


class GrafanaDataSource(Protocol):
    def build(
        self, workspace: str, project: ProjectIR
    ) -> GrafanaSourceContribution: ...
