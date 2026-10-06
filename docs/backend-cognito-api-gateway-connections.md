# Cognito → API Gateway JWT authorization

The `authenticates` connection attaches an API-owned JWT authorizer to one existing HTTP route. Configure the route on the API Gateway node, or provide an existing API Gateway → Lambda route connection, then select its exact `method` and `path`. Repeat the connection to protect more routes. A configured `ANY` route must be selected with method `ANY`; selecting `GET` does not create a separate route beneath it. WebSocket APIs and APIs defined through an OpenAPI `body` are rejected.

The Cognito node must create an application client. The API module receives the pool's native `endpoint` and `client_id` outputs through inputs. The issuer adds `https://` to the native endpoint, and the audience contains only that generated client ID. This also works when the pool and API use different provider Regions, including environment Region overrides. The authorizer reads the token from `$request.header.Authorization`; clients can send the token with the `Bearer` prefix. No JWT Lambda, invocation permission, execution role, or runtime IAM grant is created by this connection.

| Setting | Behavior |
|---|---|
| `path` | Required path of an existing route, including parameterized paths |
| `method` | Exact route method; defaults to `ANY` |
| `authorization_scopes` | Optional comma-separated scopes; omitted/null inherits route scopes or the API-level fallback, and an empty string explicitly clears scopes |

Scope names are validated and deduplicated in the backend. API Gateway accepts a token containing at least one configured route scope. With no required scopes, valid ID tokens and access tokens may both authorize the route; preview guidance calls this out. Custom scopes and the client's ability to obtain them require separate Cognito resource-server/OAuth setup. Authentication does not implement application ownership checks or other backend authorization.

All routes connected to the same pool share one authorizer. Identical duplicate connections are idempotent, while different pools or conflicting effective scopes for the same route are rejected. Existing named authorizers, IAM/custom route authorization, required API keys, and IAM-only Step Functions routes conflict with this JWT connection. A route referencing an ungenerated managed integration is rejected. Native HTTP integrations and generated Lambda integrations retain their targets while the selected route gains `authorization_type = "JWT"`, an authorizer ID, and its effective scopes. Binding resolution uses the complete project, so connection ordering does not affect Lambda route authorization.

The implementation follows the [AWS HTTP API JWT guide](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-jwt-authorizer.html), [Terraform authorizer schema](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apigatewayv2_authorizer), and [Cognito endpoint output](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_user_pool#attribute-reference).
