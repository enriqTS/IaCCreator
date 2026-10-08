"""Each producer renders its own membership expressions and native guards."""

from collections.abc import Callable
from dataclasses import dataclass

from app.generators.hcl_renderer import Expr
from app.generators.xray_ecs_filters import ecs_group_preconditions, ecs_group_selectors
from app.generators.xray_filters import (
    lambda_group_preconditions,
    lambda_group_selectors,
)


@dataclass(frozen=True)
class XRayGroupSource:
    flag: str
    selectors: Callable[[], Expr]
    preconditions: Callable[[], list[dict]]


XRAY_GROUP_SOURCES = (
    XRayGroupSource(
        "_managed_lambda_tracing", lambda_group_selectors, lambda_group_preconditions
    ),
    XRayGroupSource(
        "_managed_ecs_tracing", ecs_group_selectors, ecs_group_preconditions
    ),
)
