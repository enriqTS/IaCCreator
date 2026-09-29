# Step Functions → EventBridge

The `puts_event` connection turns one selected top-level JSONPath `Pass` state into an optimized EventBridge `PutEvents` Task state. The state retains its `Next` or `End` transition and its input, output, and result paths. The generated task sends one entry to the bus attached to the target EventBridge rule. That target can use its own generated custom bus or the account's default bus.

The connection fields are `state_name` (default `Pass`), `source` (default `iaccreator.workflow`), `detail_type` (default `Workflow Event`), and optional `detail_json`. Without `detail_json`, `Detail.$ = States.JsonToString($)` sends the state's input as a JSON string. A constant detail must be a JSON object. Set the target rule's event pattern to match the selected source and detail type, and connect a delivery target to that rule.

The EventBridge module exposes `event_bus_arn`, referencing the generated bus or a lookup of the default bus. The root module passes this ARN into the workflow module. The Task uses it as `EventBusName`, and an inline policy on the existing execution role grants `events:PutEvents` only on connected bus ARNs. Multiple event connections share one policy and deterministic state bindings. The workflow state machine depends on that policy.

The generator rejects missing execution roles, invalid JSON detail, missing or unsuitable Pass placeholders, duplicate bindings with different event settings, and states already selected by another supported workflow task connection. PutEvents reports an individual failed entry as a task failure; callers can configure state-level retry and catch behavior in the workflow definition. Retries may publish duplicate events, so consumers should handle duplicates when needed.
