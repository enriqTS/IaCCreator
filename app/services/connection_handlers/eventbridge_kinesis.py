"""Kinesis targets reuse rule-owned roles with stream-scoped record writes."""

from app.models.connection_configs.eventbridge_kinesis import EventBridgeKinesisConfig
from app.services.connection_handlers.eventbridge_role_target import (
    EventBridgeRoleTargetHandler,
)


class EventBridgeKinesisHandler(EventBridgeRoleTargetHandler):
    config_model = EventBridgeKinesisConfig

    def __init__(self):
        super().__init__(
            "stream",
            "kinesis:PutRecord",
            "stream_arn",
            "Writes matching events to the connected Kinesis stream. An optional partition key path reads a single field from the original event; it must resolve to a valid Kinesis partition key. Omit the path to use the event ID. Configure capacity, consumers, delivery retries, dead-letter handling, and monitoring separately. Consumers must tolerate duplicates. Permissions for externally configured stream encryption remain external prerequisites.",
        )

    def target_attributes(
        self, config: EventBridgeKinesisConfig, identifier: str
    ) -> dict:
        if config.partition_key_path is None:
            return {}
        return {"kinesis_target": {"partition_key_path": config.partition_key_path}}
