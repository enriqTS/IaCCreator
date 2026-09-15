"""Explicit Kafka topic and consumer-group names keep IAM grants resource scoped."""

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import ValidationRule


class MskTopicWriteConfig(BaseConnectionConfig):
    topic_name: str = ConnectionField(
        ...,
        label="Existing topic name",
        description="Concrete Kafka topic; wildcards and internal topics are excluded",
        validation=ValidationRule(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,248}$"),
    )


class MskTopicReadConfig(MskTopicWriteConfig):
    consumer_group: str = ConnectionField(
        ...,
        label="Consumer group",
        description="Concrete consumer group used by the application's Kafka client",
        validation=ValidationRule(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,248}$"),
    )
