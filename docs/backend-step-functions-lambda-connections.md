# Step Functions to Lambda tasks

Connect a Step Functions workflow to a generated Lambda function with `invokes`. Select an existing top-level JSONPath Pass state through `state_name` (default `Pass`). The connection changes it into a direct Lambda Task whose `Resource` is the function's native ARN. InputPath, OutputPath, ResultPath, Next or End, and comments are preserved; placeholder Result values are removed. Direct Lambda tasks return the function output as the task result. Each state can bind to only one target.

The workflow must have an external execution role ARN that trusts `states.amazonaws.com`. A workflow-owned inline policy grants `lambda:InvokeFunction` only on connected function ARNs. Multiple Lambda tasks share one policy. Lambda and Secrets Manager tasks can occupy different placeholders in the same workflow; overlapping bindings are rejected. The task transformation and its placeholder checks are reevaluated when Terraform environment variables override the definition.

AWS documents [direct Lambda Task resources and their IAM permissions](https://docs.aws.amazon.com/step-functions/latest/dg/connect-lambda.html). This connection uses synchronous invocation. Lambda errors fail the Task; retry and catch behavior belongs in the workflow definition.
