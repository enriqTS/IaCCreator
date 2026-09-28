"""Settings for an SNS subscription to a Firehose delivery stream."""

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField


class SnsFirehoseConfig(BaseConnectionConfig):
    raw_message_delivery: bool = ConnectionField(
        False,
        label="Raw Message Delivery",
        description="Store the published message without the SNS envelope",
        type="boolean",
    )
