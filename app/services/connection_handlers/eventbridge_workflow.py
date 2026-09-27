"""EventBridge workflow targets use asynchronous execution permissions."""

from app.services.connection_handlers.eventbridge_role_target import (
    EventBridgeRoleTargetHandler,
)


class EventBridgeWorkflowHandler(EventBridgeRoleTargetHandler):
    def __init__(self):
        super().__init__(
            "workflow",
            "states:StartExecution",
            "state_machine_arn",
            "Starts asynchronous workflow executions for matching events. The workflow execution role and definition remain separately configured. Events may be delivered more than once; make workflow actions idempotent. Configure delivery retries, dead-letter handling, alarms, and any workflow encryption permissions separately. Constant input replaces the matched event; no input transformer is generated.",
        )
