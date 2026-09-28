# API Gateway to Step Functions

Connect an HTTP API to a generated Step Functions state machine with `starts_execution`. Add a `POST` route in the gateway's route list and bind its integration to the workflow node. The backend claims that route, emits one `StepFunctions-StartExecution` integration, and sends the complete request body as the execution input. The route uses `AWS_IAM` authorization. API Gateway assumes a generated role limited to `states:StartExecution` on the connected state machine ARN.

This integration starts executions asynchronously; clients receive execution metadata rather than the workflow result. Clients must send a valid JSON body. WebSocket APIs, OpenAPI-body APIs, and non-POST routes are rejected. The workflow's execution role and any service permissions used by its states remain separately managed.

AWS describes [HTTP API service integrations](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-aws-services.html) and the [StartExecution subtype](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-aws-services-reference.html).
