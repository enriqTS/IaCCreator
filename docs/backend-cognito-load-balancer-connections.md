# Cognito → Load Balancer authentication

The `authenticates` connection adds browser sign-in to an existing HTTPS Application Load Balancer listener. First connect the ALB to a Target Group with `forwards_to` using HTTPS and the desired listener port, and connect Certificate Manager to the ALB with `secures`. Configure `domain_prefix` on the Cognito node, then connect Cognito to the ALB and supply the application's DNS hostname.

| Setting | Behavior |
|---|---|
| `listener_port` | Existing HTTPS forwarding listener; defaults to 443 |
| `application_hostname` | Required DNS hostname pointing to this ALB and covered by its certificate; normalized to lowercase |
| `scopes` | Space-separated built-in Cognito OAuth scopes, including `openid`; defaults to `openid` |
| `on_unauthenticated_request` | `authenticate` redirects to sign-in; `deny` rejects missing sessions; `allow` permits anonymous requests |
| `session_timeout` | Authentication session duration in seconds, from 1 to 604800; defaults to 3600 |

The Cognito generator creates `aws_cognito_user_pool_domain` when `domain_prefix` is configured and exports its native domain prefix. The prefix must contain lowercase letters, numbers, or internal hyphens, be at most 63 characters, and exclude `aws`, `amazon`, and `cognito`. AWS requires the prefix to be available within the Region. Custom Cognito domains and federated identity providers are outside this connection's current scope.

Each authenticated listener gets a dedicated confidential `aws_cognito_user_pool_client` in the ALB module. It enables the authorization-code flow, generates a secret, uses the selected scopes, and accepts the callback `https://<application_hostname>/oauth2/idpresponse` (including the listener port when it differs from 443). The public client used by API Gateway and AppSync remains independent; ALB authentication works with the Cognito node's `create_client` disabled. The generated project does not export the confidential client's secret, although Terraform retains it in state.

Pool ID, ARN, and domain cross into the ALB module as inputs. The client consumes the pool ID; the listener consumes the pool ARN/domain and the local client ID. The existing listener receives an `authenticate-cognito` action at order 1 followed by its original forward action at order 2. The explicit callback hostname avoids a reverse dependency from the Cognito module to the ALB module. Each listener has a deterministic distinct session-cookie name.

The resolver uses the complete project, so connection ordering does not change authentication. Identical duplicates are idempotent. Conflicting settings or different pools on one listener, ambiguous forwarding targets, missing domain/certificate/listener connections, non-HTTPS listeners, Network/Gateway Load Balancers, and non-HTTP(S) target groups are rejected. The existing listener generator owns one listener per target group; using that same target group for multiple listener ports is rejected when authentication is present. Distinct target groups can support separate authenticated listener ports. Other listeners retain their original forwarding behavior.

The generated client uses the ALB module's AWS provider, so this implementation requires the ALB and pool in the same Region. Validation checks effective Regions, including inherited project defaults and environment Region overrides. A native ARN precondition also guards the client at Terraform apply.

DNS records, certificate validation, user provisioning, and network reachability must be configured for the deployment. The current certificate connection chooses the first connected certificate by node name; ensure that certificate covers the application hostname. An ALB needs outbound IPv4 HTTPS connectivity to Cognito's token and user-info endpoints, which may require NAT for an internal ALB. The Terraform principal needs `cognito-idp:DescribeUserPoolClient`. Preview reports these requirements and flags `allow` as optional authentication. The backend must enforce application authorization and verify ALB-signed user claims, including the expected ALB signer; users must not be able to bypass the ALB and reach protected targets directly.

Behavior follows the [AWS ALB authentication guide](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/listener-authenticate-users.html), [Cognito domain-prefix guide](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-assign-domain-prefix.html), [Terraform listener schema](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lb_listener), and [Terraform Cognito client schema](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_user_pool_client).
