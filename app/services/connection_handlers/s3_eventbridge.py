"""Enable bucket events and scope a default-bus rule to connected buckets."""

import json

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.s3_notifications import S3Notifications


class S3EventBridgeHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        target = self._find_instance(connection.target_name, project)
        config = target.config
        try:
            if config.bus_name is not None or config.schedule_expression:
                raise ValueError(
                    "Direct S3 delivery requires an unscheduled rule on the default event bus"
                )
            pattern = json.loads(config.event_pattern or "{}")
            if not isinstance(pattern, dict) or "$or" in pattern:
                raise ValueError(
                    "S3 rules require an object event pattern without top-level $or"
                )
            detail = pattern.get("detail", {})
            if not isinstance(detail, dict) or "$or" in detail:
                raise ValueError("S3 rule detail must be an object without $or")
            bucket_filter = detail.get("bucket", {})
            if not isinstance(bucket_filter, dict):
                raise ValueError("S3 rule bucket filter must be an object")
        except (ValueError, TypeError) as exc:
            raise InvalidConnectionConfigError(
                connection.source_name,
                target.name,
                connection.connection_type,
                [{"loc": ("event_pattern",), "msg": str(exc)}],
            ) from exc
        buckets = sorted(
            {
                item.source_name
                for item in project.connections
                if item.source_service == ServiceType.S3
                and item.target_name == target.name
                and item.connection_type == "delivers_to"
            }
        )
        pattern["source"] = ["aws.s3"]
        pattern["detail"] = {
            **detail,
            "bucket": {
                **bucket_filter,
                "name": [Expr(f"module.{name}.bucket_name") for name in buckets],
            },
        }
        config.event_pattern = config.event_pattern or "{}"
        result = S3Notifications().handle(connection, project)
        result.inputs.append(
            ModuleInput(
                module=target.name,
                name="event_pattern",
                value=self._renderer.render_json_policy(pattern),
                description="Event pattern scoped to connected S3 buckets",
            )
        )
        return result
