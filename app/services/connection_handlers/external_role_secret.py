"""Scoped secret access on an externally owned execution role."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.ir_models import ConnectionIR, ProjectIR
from app.services.connection_handlers.secret_access import SecretAccessHandler


class ExternalRoleSecretAccessHandler(SecretAccessHandler):
    def __init__(self, role_field: str, label: str) -> None:
        super().__init__()
        self._role_field = role_field
        self._label = label

    def _role_reference(self, connection: ConnectionIR, project: ProjectIR) -> Expr:
        instance = self._find_instance(connection.source_name, project)
        if instance is None or not getattr(instance.config, self._role_field, None):
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": (self._role_field,),
                        "msg": f"{self._label} secret access requires a service role ARN",
                    }
                ],
            )
        return Expr(f'element(reverse(split("/", var.{self._role_field})), 0)')
