"""ActiveMQ client protocol selection exposes TLS endpoints without credentials."""

from typing import Literal

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs._metadata import ConnectionField
from app.models.input_models._metadata import OptionEntry

MQ_PROTOCOL_SCHEMES = {
    "amqp": "amqp+ssl",
    "openwire": "ssl",
    "stomp": "stomp+ssl",
    "mqtt": "mqtt+ssl",
    "websocket": "wss",
}


class MqClientConfig(BaseConnectionConfig):
    protocol: Literal["amqp", "openwire", "stomp", "mqtt", "websocket"] = (
        ConnectionField(
            "amqp",
            label="Client protocol",
            description="TLS endpoint protocol; WebSocket clients negotiate MQTT or STOMP",
            type="select",
            options=[
                OptionEntry(value="amqp", label="AMQP over TLS"),
                OptionEntry(value="openwire", label="OpenWire over TLS"),
                OptionEntry(value="stomp", label="STOMP over TLS"),
                OptionEntry(value="mqtt", label="MQTT over TLS"),
                OptionEntry(value="websocket", label="Secure WebSocket"),
            ],
        )
    )
