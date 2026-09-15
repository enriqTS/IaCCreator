# ActiveMQ client endpoint connections

Lambda and ECS support `connects_to` connections to Amazon MQ. The current MQ service node provisions ActiveMQ, so this integration exposes ActiveMQ client endpoints only. It does not grant message read/write access or create a Lambda event-source mapping.

The typed `protocol` selector defaults to `amqp` and offers:

| Protocol | Native TLS endpoint scheme |
| --- | --- |
| `amqp` | `amqp+ssl://` |
| `openwire` | `ssl://` |
| `stomp` | `stomp+ssl://` |
| `mqtt` | `mqtt+ssl://` |
| `websocket` | `wss://` |

WebSocket clients must negotiate the appropriate MQTT or STOMP subprotocol. Endpoint URI syntax may need adaptation for the application library; the generator preserves AWS's returned URI instead of guessing a client-specific format. See [AWS ActiveMQ broker endpoints](https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/amazon-mq-basic-elements.html).

The broker module exports `client_<protocol>_endpoints`, a sorted, deduplicated list filtered from every native `aws_mq_broker.instances[*].endpoints` entry. Selection uses the URI scheme, not provider list positions. Console URLs and other protocols are excluded. A typed `list(string)` module input passes those values to each client, whose `mq_<broker-node-name>_<protocol>_client` output contains `engine`, `protocol`, `endpoints`, and `tls=true`.

Both endpoints of an active/standby broker are retained. Their sort order does not identify the active instance. Configure the application's protocol-specific failover or reconnect support using the full list; this relationship does not select an active broker or construct a library-specific failover URI. Single-instance brokers use the same list format.

Broker users and queue/topic authorization remain separately managed. ActiveMQ messaging uses its broker authentication and destination permissions, rather than IAM management permissions. This connection neither copies the configured broker username/password nor creates or reads credentials. It adds no IAM statements and leaves existing runtime policies unchanged. See [AWS ActiveMQ authentication and authorization](https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/amazon-mq-access.html).

Existing Lambda `reads_secret` or ECS `injects_secret` connections can independently deliver an application's broker credentials from Secrets Manager. Populate the secret and configure its corresponding broker user and destination permissions separately. The MQ node's existing initial-user configuration is unchanged; an endpoint connection does not make that administrator account the application identity.

Applications must consume the exported metadata, enable TLS verification, and configure credentials and destinations. Subnets, security groups, routes, and broker accessibility remain separate. Existing Subnet/Security Group → MQ connections continue to handle placement. Cross-Region endpoint bindings are allowed but do not establish network connectivity.

Multiple protocols and brokers produce distinct client outputs. Multiple clients sharing a broker reuse its protocol output. Duplicate and reordered connections generate identical projects. Tests evaluate the endpoint-selection expression with Terraform, check composition with secret delivery, and validate generated projects and dependency graphs; they do not test live broker login.
