# Fault Injection Simulator EC2 targets

`Fault Injection Simulator → EC2` (`targets`) configures an experiment template with explicit connected instances. `FisEc2Config.operation` defaults to `reboot`; `stop` leaves instances stopped until an operator restarts them. `selection_mode` defaults to `COUNT(1)` and also accepts `COUNT(2)` through `COUNT(5)` or `ALL`. A template accepts one to five distinct connected instances, and a count cannot exceed that set. All its edges must select the same operation and selection mode. AWS limits explicit target ARN lists to five entries. [AWS target input reference](https://docs.aws.amazon.com/fis/latest/APIReference/API_CreateExperimentTemplateTargetInput.html).

## Ownership and wiring

The FIS module owns the template and its role policy. Instance modules export `fis_instance`, a typed object containing the native ARN and whether the root is EBS-backed without stop protection. These objects enter the template through `fis_ec2_targets`; `fis_ec2_action` carries the operation and selection. Unique target names sort deterministically, repeated edges are idempotent, and multiple templates may share instances. `ec2_target_arns` exports the explicit eligible set rather than a prediction of which instances an experiment will select.

Each template supports one target service type. Use a separate template for [ECS task targets](backend-fis-ecs-connections.md); mixed EC2/ECS target connections are rejected before contribution generation.

The template has one `managed_ec2` target of type `aws:ec2:instance`. Its action uses `aws:ec2:reboot-instances` or `aws:ec2:stop-instances` and maps `Instances` to that target. The connection supersedes the standalone `action_id` field while preserving the action name, description, external role ARN, and existing `source = "none"` stop condition. Explicit targets use no tag or resource filters; AWS disallows filters with explicit resource ARNs. [AWS target selection guide](https://docs.aws.amazon.com/fis/latest/userguide/targets.html).

`FaultInjectionSimulatorGenerator` derives `template_arn` from native template ID and deployment partition, Region, and account. The provider exposes `id`, not an ARN attribute. The same identity data sources support connection guards. Unconnected templates retain their standalone action configuration. [Provider resource reference](https://github.com/hashicorp/terraform-provider-aws/blob/main/website/docs/r/fis_experiment_template.html.markdown), [AWS template ARN format](https://docs.aws.amazon.com/service-authorization/latest/reference/list_fis.html).

## Permissions and validation

`ec2_targets.tf` attaches one inline policy to the configured external experiment role, with a generated name prefix to avoid collisions. The native IAM role lookup resolves the basename; a precondition compares the entire returned ARN, including its path, before attachment. The role must be in the deployment account and partition. Its trust policy remains externally owned and must allow `fis.amazonaws.com`, with suitable source-account and experiment-ARN restrictions. The deployment identity needs role lookup, inline-policy management, and permission to pass the role to FIS. Shared roles retain the union of their attached permissions. [AWS experiment-role guide](https://docs.aws.amazon.com/fis/latest/userguide/getting-started-iam-service-role.html).

Reboot grants `ec2:RebootInstances` only on connected native instance ARNs. Stop grants AWS's required `ec2:StopInstances` and `ec2:StartInstances` on those ARNs, although the generated action omits automatic restart. Both policies grant `ec2:DescribeInstances` on `*`, constrained to the deployment Region. There are no termination permissions or KMS grants. [AWS action permissions and parameters](https://docs.aws.amazon.com/fis/latest/userguide/fis-actions-reference.html).

Backend validation rejects conflicting settings, malformed roles/action names, excessive target counts, out-of-bounds selection, and effective Region mismatches, including environment overrides. Template and policy preconditions additionally check native instance ARN format, partition, Region, account, unique ARN count, action name, selection, operation, and stop eligibility. Policy attachment performs these checks as well as the exact role identity check before widening role permissions.

## Execution and recovery

Terraform creates the template and policy; it never starts an experiment. An operator must check instance state and eligibility at execution time. Stop requires an EBS-backed root and disabled stop protection. Automatic restart, alarm-based stop conditions, encrypted-instance restart grants, and workload recovery are outside this connection. Plan manual recovery, possible instance-store data loss on stop, and experiment charges before execution.

## Verification

`tests/test_fis_ec2_connections.py` covers property-based aggregation and connector order, typed settings, invalid/conflicting bindings, effective Regions, preview guidance, native stop metadata and scope guards, actual emitted IAM policy evaluation, exact role paths, and ARN derivation in AWS and China partitions. Provider validation and plan graphs cover reboot, stop, repeated edges, five-target ALL/count selection, shared instances/roles, EC2 secrets/EBS composition, regional providers, and unconnected templates. Schema endpoint tests verify dynamic discovery. No tests deploy resources or run faults.
