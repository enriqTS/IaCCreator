"""Apply managed JWT authorization to an existing HTTP route resource."""

from app.generators.hcl_renderer import Expr
from app.models.api_gateway_authentication import CognitoJwtRouteBinding


def apply_cognito_jwt_authorization(
    attrs: dict,
    bindings: dict[tuple[str, str], CognitoJwtRouteBinding],
    method: str,
    path: str,
) -> None:
    binding = bindings.get((method.upper(), path))
    if binding is not None:
        attrs.update(
            authorization_type="JWT",
            authorizer_id=Expr(
                f"aws_apigatewayv2_authorizer.{binding.authorizer_resource}.id"
            ),
            authorization_scopes=list(binding.scopes),
        )
