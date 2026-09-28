"""EventBridge starts a standard build in the connected CodeBuild project."""

from app.models.connection_configs.eventbridge_codebuild import (
    EventBridgeCodeBuildConfig,
)
from app.services.connection_handlers.eventbridge_role_target import (
    EventBridgeRoleTargetHandler,
)


class EventBridgeCodeBuildHandler(EventBridgeRoleTargetHandler):
    config_model = EventBridgeCodeBuildConfig

    def __init__(self):
        super().__init__(
            "build",
            "codebuild:StartBuild",
            "project_arn",
            "Starts a standard build in the connected CodeBuild project. Configure the buildspec, source, artifact handling, retries, dead-letter handling, and monitoring separately.",
        )
