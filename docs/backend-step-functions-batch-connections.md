# Step Functions to Batch jobs

Connect a Step Functions workflow to a generated Batch queue with `submits_job`. Select an existing top-level JSONPath Pass state through `state_name` (default `Pass`) and a generated Batch job definition through `job_definition_name`. The connection replaces the Pass state with a `batch:submitJob.sync` Task that waits for the job to complete. `job_name` defaults to `workflow-job`; optional `array_size` and `job_attempts` control array jobs and retries. Existing transitions and data paths remain, while placeholder Result values are removed.

The workflow's external execution role must trust `states.amazonaws.com`. A workflow-owned policy scopes `batch:SubmitJob` to the selected generated queue and revision-qualified job definition ARNs. It also grants `batch:DescribeJobs` and `batch:TerminateJob` on `*`, because job IDs are assigned at runtime, plus permissions on the Step Functions Batch completion rule. The generated Batch target uses an unmanaged compute environment with a service role; supply its compute capacity separately.

Batch states can share a workflow with Lambda, ECS, and Secrets Manager states. Duplicate or overlapping state bindings are rejected. Terraform preconditions check the selected placeholders again if the workflow definition is overridden by variables. Configure container behavior, capacity, monitoring, and any job-specific timeout or failure handling for your deployment.

AWS documents [synchronous Batch tasks](https://docs.aws.amazon.com/step-functions/latest/dg/connect-batch.html) and [scoping SubmitJob to queues and job definitions](https://docs.aws.amazon.com/batch/latest/userguide/iam-example-restrict-job-submission.html).
