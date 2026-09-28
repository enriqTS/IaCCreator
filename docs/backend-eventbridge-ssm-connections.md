# EventBridge to Systems Manager Command documents

Connect an EventBridge rule to a generated Systems Manager `Command` document with the `targets` connection. Set `instance_id` to one managed EC2 instance ID; `target_id` is optional. The target uses `run_command_targets` and the document ARN exported by its module. The rule module creates an invocation role trusted by EventBridge for that rule only. Its `ssm:SendCommand` policy is limited to the document ARN and the selected EC2 instance ARN.

Automation and Policy documents are rejected. The target also checks the document type during Terraform validation so an environment override cannot turn the connected document into an incompatible type. Document parameters, tag-based targeting, and multiple instances per connection are not configured by this connection. The selected EC2 instance must already be a Systems Manager managed node with a working agent, instance profile, and network path to Systems Manager.

AWS documents the required target selector and invocation permissions in its [EventBridge target guide](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-targets.html) and [EventBridge IAM role guide](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-events-iam-roles.html).
