# AppSync → Lambda

The `resolves_with` connection binds an AppSync GraphQL field to a Lambda function. Set `type_name` (default `Query`) and the required `field_name` to identify the field. The AppSync node must supply `schema_definition` containing that type and field. The connection checks that a schema is present and that both names are valid GraphQL names; AppSync validates the full schema and field binding during deployment.

The AppSync module owns the generated `AWS_LAMBDA` data source and direct unit resolver. With no request or response mapping templates, AppSync sends the resolver context to Lambda and maps its response to the GraphQL field. The function must return a value compatible with the field's GraphQL type.

The same module creates a service role trusted by `appsync.amazonaws.com` only for that API ARN. Its policy grants `lambda:InvokeFunction` on the connected function ARN. The Lambda module exports its native ARN through a root-module input, so the AppSync module has no direct reference to a foreign resource. Each Lambda uses one data source and role even if multiple fields resolve through it; each field has one resolver. Conflicting Lambda selections for a field are rejected, and repeated identical connections are idempotent.

The generated resources follow the [Terraform AppSync data-source reference](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appsync_datasource) and [AWS direct Lambda resolver behavior](https://docs.aws.amazon.com/appsync/latest/devguide/direct-lambda-reference.html). The role trust uses the [AppSync source-ARN condition](https://docs.aws.amazon.com/appsync/latest/devguide/attaching-a-data-source.html).
