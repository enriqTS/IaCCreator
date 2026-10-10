# ECR application images in ECS

ECR → ECS (`runs_image`) supplies native private repository references and an explicit image version to an application container. `container_name` defaults to the ECS node name; `image_version` defaults to `latest` and accepts a literal Docker tag or a lowercase `sha256:<64 hex characters>` digest. A tag produces `<repository_url>:<tag>`; a digest produces `<repository_url>@<digest>`.

## Containers and deployment

ECS exposes optional `container_definitions` as a JSON array. The backend normalizes it and requires at least one uniquely named container with a nonempty string image, preserving other fields. When omitted, the existing single placeholder container remains, including port mappings derived from Target Group connections. Select an existing application container when using custom definitions; custom port mappings must agree with connected load balancers.

The image transformation replaces only the selected container's image. It composes after runtime secrets, EFS mounts, and application logging, before managed X-Ray/Prometheus collectors are appended. Command, environment, ports, health checks, and other application settings remain intact; Terraform template markers inside configured JSON remain literal. Managed collectors retain their own public images and cannot be selected by this connection. Remove external `repositoryCredentials` from selected containers.

This connection requires the modeled Linux Fargate task, subnet placement, and security-group placement. Existing external subnet/security-group identifiers and pending managed placement connections are supported. Each repository and task must share the effective Region in every environment; a global environment Region override can align their placement.

Push an image compatible with the task platform before applying the generated project. The connection does not build, push, look up, or scan images and does not check whether a selected tag or digest exists. Terraform changes to an ECS service/task can start or replace tasks. Updating content under an unchanged mutable tag does not change the Terraform reference or force a rollout. Prefer immutable tags or digests when releases need an explicit change in configuration. ECR API/registry and S3 image-layer network access, deployment capacity, and permission to pass the execution role remain prerequisites.

## References, permissions, and ownership

The repository exports its native name alongside existing ARN and URL outputs. A typed `registry_images` map carries repository metadata and image selectors into the task module, which exports effective image references. No credentials or authorization-token data sources are generated and no reverse repository dependency is introduced.

The task reuses its existing generated execution role. Its baseline policy retains `ecr:GetAuthorizationToken` and existing CloudWatch log actions on `*`; repository pull actions move out of that wildcard baseline into an ECS-owned `registry_images.tf` inline policy:

- `ecr:BatchCheckLayerAvailability`
- `ecr:GetDownloadUrlForLayer`
- `ecr:BatchGetImage`

These actions use the sorted, distinct native repository ARNs across all connected application containers. Every application container using a private ECR image must have a connection so its pull permissions are explicit; public ECR and other external images remain untouched. The image connection alone does not assign application task credentials, but other connections may reuse the same generated role as both task and execution role. Unconnected tasks retain their existing baseline behavior. Publication, repository policies, cross-account pulls, and cross-Region pulls are outside this connection.

Identical duplicate bindings are idempotent, including repeated Target Group load-balancer entries in composed tasks. Different repositories or versions for the same container fail. Several containers can use the same repository, several repositories can serve one task, and one repository can serve several tasks. Each task retains all inline-policy dependencies and existing lifecycle guards.

Terraform preconditions verify selected application containers, unique names, bounded repository/container/version syntax, absent external registry credentials, complete private-image coverage, and Fargate placement. Native repository ARN, name, and URL must agree with the task caller's account, partition, and Region. Commercial AWS, GovCloud, and China standard registry URLs are supported. These guards protect edited module inputs; they do not prove image availability, compatibility, role trust, or network readiness.

## Validation

`tests/test_ecr_ecs_connections.py` covers property-based names, versions, sharing, duplicate order, container JSON preservation and invalid inputs, scoped baseline/pull permissions, actual Terraform image and guard evaluation, application/collector composition, and ten cached-provider validation/dependency-graph projects. These include multiple repositories, managed placement, Target Group wiring, encrypted logs, collectors, EFS/secrets, and EventBridge invocation. API tests cover schema discovery, and the generated frontend service schemas include the optional container JSON field. Validation makes no AWS calls or deployments.

References: [ECS task execution role](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html), [ECS task definition parameters](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html), [ECS deployment behavior](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-type-ecs.html), [ECR repository naming](https://docs.aws.amazon.com/AmazonECR/latest/APIReference/API_CreateRepository.html), and [Terraform ECS task definitions](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecs_task_definition).
