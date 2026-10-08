"""Shared group validation and references preserve producer ownership."""

import re

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.generators.xray_filters import XRAY_GROUP_NAME_PATTERN, render_xray_scope_data
from app.models.input_models.xray_config import XRayConfig
from app.models.ir_models import ConnectionContribution, ModuleInput, ModuleResource
from app.services.connection_handlers.base import BaseConnectionHandler


def group_configuration_errors(config: XRayConfig) -> list[dict]:
    errors = []
    if (
        not re.fullmatch(XRAY_GROUP_NAME_PATTERN, config.group_name)
        or config.group_name == "Default"
    ):
        errors.append(
            {
                "loc": ("group_name",),
                "msg": "Use a concrete non-reserved X-Ray group name",
            }
        )
    if not config.filter_expression.strip():
        errors.append(
            {
                "loc": ("filter_expression",),
                "msg": "The additional group filter must be nonempty",
            }
        )
    if config.notifications_enabled and not config.insights_enabled:
        errors.append(
            {
                "loc": ("notifications_enabled",),
                "msg": "Insights notifications require Insights",
            }
        )
    return errors


def group_membership_contribution(
    target: str,
    members: list[str],
    input_name: str,
    arn_output: str,
    name_output: str,
) -> ConnectionContribution:
    return ConnectionContribution(
        inputs=[
            ModuleInput(
                module=target,
                name=input_name,
                type="map(object({ arn = string, name = string }))",
                value=HCLRenderer().render_expression(
                    {
                        name: {
                            "arn": Expr(f"module.{name}.{arn_output}"),
                            "name": Expr(f"module.{name}.{name_output}"),
                        }
                        for name in members
                    }
                ),
                description="Native producer identities selecting traces for this X-Ray group",
            )
        ],
        resources=[
            ModuleResource(
                module=target,
                filename="xray_tracing.tf",
                content=render_xray_scope_data(),
            )
        ],
        outputs=[
            BaseConnectionHandler._output(
                target,
                "trace_filter_expression",
                f"aws_xray_group.{target}.filter_expression",
                "Effective native trace filter including connected producers",
            )
        ],
    )
