# Step Functions to ECS Fargate tasks

Connect a Step Functions workflow to a generated ECS node with `runs_task`. Select an existing top-level JSONPath Pass state through `state_name` (default `Pass`). The connection replaces it with an `ecs:runTask.sync` Task that waits for the Fargate task to stop. It uses the connected cluster, task definition, subnets, security groups, and public-IP setting; `task_count` defaults to one and accepts 1–10. Existing state transitions and data paths remain in place, and placeholder Result values are removed.

The workflow's external execution role must trust `states.amazonaws.com`. A workflow-owned inline policy grants RunTask on the selected task definitions in the selected clusters, PassRole on their task roles, task monitoring, and access to the Step Functions ECS completion rule. AWS requires task monitoring actions on `*` because task IDs do not exist until launch. The ECS node must have Fargate-compatible configuration and at least one subnet. Its separate ECS service remains a distinct resource; set its desired count for your deployment needs.

Lambda and Secrets Manager task connections can occupy other placeholders in the same workflow. Overlapping state bindings are rejected. Task networking and state transitions are checked again when Terraform variables override the workflow definition. Container logic, image access, networking, retries, and logging need their own configuration.

AWS describes the [ECS integration and its IAM requirements](https://docs.aws.amazon.com/step-functions/latest/dg/connect-ecs.html).
