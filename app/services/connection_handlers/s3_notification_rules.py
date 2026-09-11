"""Validate managed notification filters before rendering bucket configuration."""

from itertools import combinations
from urllib.parse import unquote_plus

from app.exceptions import InvalidConnectionConfigError
from app.models.ir_models import ConnectionIR


def notification_key(connection: ConnectionIR) -> tuple:
    config = connection.connection_config
    return (
        connection.target_name,
        tuple(sorted(set(config.get("events") or ["s3:ObjectCreated:*"]))),
        config.get("filter_prefix") or "",
        config.get("filter_suffix") or "",
    )


def validate_notification_filters(connections: list[ConnectionIR]) -> None:
    for first, second in combinations(connections, 2):
        _, events_a, prefix_a, suffix_a = notification_key(first)
        _, events_b, prefix_b, suffix_b = notification_key(second)
        prefix_a, prefix_b, suffix_a, suffix_b = map(
            unquote_plus, (prefix_a, prefix_b, suffix_a, suffix_b)
        )
        if (
            set(events_a) & set(events_b)
            and (prefix_a.startswith(prefix_b) or prefix_b.startswith(prefix_a))
            and (suffix_a.endswith(suffix_b) or suffix_b.endswith(suffix_a))
        ):
            raise InvalidConnectionConfigError(
                first.source_name,
                second.target_name,
                "notifies",
                [
                    {
                        "loc": ("filter_prefix", "filter_suffix"),
                        "msg": "S3 notification filters must not overlap for the same event types; use SNS fan-out for multiple consumers",
                    }
                ],
            )
