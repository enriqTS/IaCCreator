"""EventBridge topic targets publish through dedicated invocation roles."""

from app.services.connection_handlers.eventbridge_role_target import (
    EventBridgeRoleTargetHandler,
)


class EventBridgeSNSHandler(EventBridgeRoleTargetHandler):
    def __init__(self):
        super().__init__(
            "topic",
            "sns:Publish",
            "topic_arn",
            "Publishes matching events to a standard SNS topic through a dedicated role. Configure subscribers, delivery retries, dead-letter handling, and monitoring separately. Subscribers must tolerate duplicates. Constant JSON input replaces the matched event. Topic and KMS key policies must permit the invocation role; external key policies are not modified.",
            reject_fifo=True,
        )
