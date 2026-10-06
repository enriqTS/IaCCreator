# Cognito → AppSync authentication

The `authenticates` connection configures the generated AppSync GraphQL API to accept tokens from the connected Cognito user pool. User-pool and client IDs cross into the API module through inputs; the pool's Region is exported from its native ARN, so provider aliases and environment Region overrides remain consistent. Authentication adds no runtime IAM policy or service role.

| Setting | Default | Behavior |
|---|---|---|
| `mode` | `default` | Replace the API's authentication with Cognito, or add Cognito as an `additional` provider |
| `restrict_to_client` | `true` | Match only the generated app client with an anchored client-ID expression |
| `default_action` | `ALLOW` | Default field access for a default Cognito provider; `DENY` requires explicit group directives |

With default Cognito authentication, the generator omits AppSync API-key resources and their outputs even if the API node's original settings selected API keys. Additional Cognito authentication preserves the node's API-key or IAM default. An API can have one default pool and multiple distinct additional pools. Repeated identical connections are idempotent; conflicting settings for the same pool and multiple default pools are rejected. Default `DENY` cannot be combined with additional providers.

Client restriction requires the Cognito node's `create_client` option. To use existing clients without creating one, explicitly disable `restrict_to_client`; the API then accepts tokens from any client in that pool. The connection does not accept arbitrary client-ID expressions or copy identifiers into the API configuration.

Supply the GraphQL schema on the AppSync node. For an additional provider, use `@aws_cognito_user_pools` on the intended fields and returned types. When a sole default Cognito provider uses `DENY`, use `@aws_auth(cognito_groups: [...])` and configure the groups and memberships separately. With multiple authentication modes, use `@aws_cognito_user_pools` instead of `@aws_auth`. Preview guidance calls out these requirements; the connection preserves the supplied schema. User ownership checks and other application authorization belong in the schema/resolvers. Signing in, user/group provisioning, OAuth/domain settings, and application token handling are separate concerns.

The implementation follows the [Terraform API resource schema](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appsync_graphql_api), [AWS authorization guide](https://docs.aws.amazon.com/appsync/latest/devguide/security-authz.html), and [AWS default-action constraints](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-appsync-graphqlapi-userpoolconfig.html).
