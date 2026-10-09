# Fault Injection Simulator ECS task targets

`Fault Injection Simulator → ECS` (`targets`) configures an `aws:ecs:stop-task` experiment template for the connected ECS service. `FisEcsConfig.selection_mode` defaults to `COUNT(1)` and accepts `COUNT(2)` through `COUNT(5)` or `ALL`. Each template selects one service; repeated edges must agree on selection, and different templates may share the service or external experiment role. A template cannot mix EC2, ECS, and EKS target connections.

## Ownership and dynamic discovery

The ECS module exports `fis_service`, a typed object containing native cluster ARN/name and service ARN/name. The service ARN uses the provider's native resource ID. These values enter the FIS module through `fis_ecs_service`, alongside the separate `fis_ecs_selection` input. The FIS module exports `ecs_target`, containing the native selector metadata and selection mode.

The template owns one `managed_ecs` target of type `aws:ecs:task`. Its resource parameters identify the native cluster and service, and a `LastStatus = RUNNING` filter excludes tasks that are not running. The stop action maps `Tasks` to this target. There are no explicit runtime task ARNs, task tag selectors, action parameters, or copied cluster identifiers. AWS documents cluster/service parameters for discovering task targets. [AWS task target selection](https://docs.aws.amazon.com/fis/latest/userguide/targets.html).

The connection supersedes the standalone FIS `action_id` field and preserves description, action name, external role ARN, and the existing `source = "none"` stop condition. It adds no ECS resources or task-definition modifications, SSM sidecars, account ARN-format settings, cluster draining, or stress/network actions. Existing secrets, EFS mounts, logging, tracing, metrics, networking, and service settings retain their ownership. [AWS stop-task action](https://docs.aws.amazon.com/fis/latest/userguide/fis-actions-reference.html), [provider target parameters](https://github.com/hashicorp/terraform-provider-aws/blob/main/website/docs/r/fis_experiment_template.html.markdown).

## Permissions and identity

`ecs_targets.tf` attaches one experiment-owned inline policy to the configured external role. A generated policy name prefix permits shared roles. The native IAM role lookup resolves the basename, then checks the full returned ARN, including the path, before attaching the policy. The role must belong to the deployment partition and account. Trust for `fis.amazonaws.com`, appropriate source-account/experiment-ARN restrictions, permission boundaries, and explicit denies remain externally managed. The deployment identity needs role lookup, inline-policy management, and permission to pass the role to FIS. [AWS experiment role guide](https://docs.aws.amazon.com/fis/latest/userguide/getting-started-iam-service-role.html).

`ecs:DescribeTasks` and `ecs:StopTask` are limited to the connected cluster's long task ARN prefix, the exact `ecs:cluster` ARN condition, and deployment Region. `ecs:ListTasks` uses resource `*` with the same cluster and Region conditions. AWS-required `tag:GetResources` discovery uses resource `*` with a Region condition. There are no permissions to run tasks, change services, drain instances, issue SSM commands, or administer KMS keys. [ECS resource and condition scopes](https://docs.aws.amazon.com/service-authorization/latest/reference/list_ecs.html), [AWS cluster condition example](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/security_iam_id-based-policy-examples.html).

The service selector limits this template's target resolution; it is not an IAM boundary. These task permissions cover other services and standalone tasks in the same cluster. Shared experiment roles retain the union of all attached permissions. Use dedicated clusters and roles when stronger isolation is required.

## Validation and execution

Backend validation checks selection settings, single-service ownership, repeated-edge agreement, target-family conflicts, external role/action-name syntax, and effective Regions, including environment overrides. Template and policy preconditions check native cluster scope, cluster name/ARN agreement, long service ARN/name/cluster agreement, selection, and action-name bounds. Policy attachment additionally checks exact role identity. Long service and task ARNs are required; legacy short ARNs are not accommodated by widening the policy.

Terraform creates the template and policy; it does not start experiments. AWS discovers eligible running tasks when an operator starts an experiment. Counts are not checked against diagram desired count because actual availability changes with scaling and deployments. Missing eligible tasks or an unavailable selection count can fail execution, while `ALL` follows the service's current scale.

Stopping a task stops all its containers, including collectors, and can interrupt requests or lose ephemeral data. The ECS scheduler may launch replacements according to desired count, available capacity, permissions, networking, and workload health; this connection neither launches replacement tasks nor verifies recovery. Alarm-based stops remain unconfigured. Review running-task availability, replacement health, and experiment charges before execution. [ECS StopTask behavior](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_StopTask.html).

## Verification

`tests/test_fis_ecs_connections.py` covers property-based naming/selection/duplicate behavior, invalid settings, ownership conflicts, mixed EC2/ECS rejection, effective Regions, previews, unchanged ECS resources, native override guards, exact role paths, and emitted policy evaluation. Nine generated projects pass Terraform validation and plan graphs, including shared services/roles, separate EC2/ECS templates, Secrets Manager composition, and combined encrypted logs/X-Ray/Prometheus/EFS/Grafana wiring. Schema endpoint tests verify dynamic discovery. Tests never deploy resources or execute faults.
