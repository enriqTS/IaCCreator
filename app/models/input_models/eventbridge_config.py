"""EventBridge-specific configuration model."""

import re
from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import (
    OptionEntry,
    TerraformField,
    ValidationRule,
)


class EventBridgeConfig(BaseServiceConfig):
    """An EventBridge rule, optionally on its own event bus."""

    service_type: Literal[ServiceType.EVENTBRIDGE] = ServiceType.EVENTBRIDGE

    owns_execution_role: ClassVar[bool] = False

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "rule_name",
        "description",
        "bus_name",
        "event_pattern",
        "schedule_expression",
        "state",
        "tags",
    )

    # ── General ───────────────────────────────────────────────────────────
    rule_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the EventBridge rule",
    )
    bus_name: str | None = TerraformField(
        None,
        group="General",
        description="Custom event bus to create and attach the rule to",
    )

    # ── Matching ──────────────────────────────────────────────────────────
    event_pattern: str | None = TerraformField(
        None,
        group="Matching",
        description="JSON event pattern the rule matches",
    )
    schedule_expression: str | None = TerraformField(
        None,
        group="Matching",
        description="Schedule such as rate(5 minutes) or cron(0 12 * * ? *)",
    )
    state: str | None = TerraformField(
        None,
        group="Matching",
        description="Whether the rule is enabled",
        options=[
            OptionEntry(value="ENABLED", label="Enabled"),
            OptionEntry(value="DISABLED", label="Disabled"),
        ],
        validation=ValidationRule(allowed_values=["ENABLED", "DISABLED"]),
    )

    # AWS accepts only rate(...) and cron(...) schedules
    _SCHEDULE: ClassVar[re.Pattern] = re.compile(r"^(rate|cron)\(.+\)$")

    def validate_for_generation(self) -> None:
        """A rule with neither a pattern nor a schedule cannot be created by AWS."""
        if not self.event_pattern and not self.schedule_expression:
            raise ValueError(
                "an EventBridge rule needs either event_pattern or schedule_expression"
            )
        if self.schedule_expression and not self._SCHEDULE.match(
            self.schedule_expression
        ):
            raise ValueError(
                "schedule_expression must look like rate(5 minutes) or cron(0 12 * * ? *)"
            )
