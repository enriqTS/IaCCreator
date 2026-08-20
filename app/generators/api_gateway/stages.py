"""Deployment stages, access logging and default route settings."""

from app.generators.api_gateway._support import sanitize_route_name
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.api_gateway_config import ApiGatewayConfig
from app.models.ir_models import ResourceInstanceIR


def render_stages(
    instance: ResourceInstanceIR, config: ApiGatewayConfig, r: HCLRenderer
) -> str:
    """Generate aws_apigatewayv2_stage resources and associated CloudWatch log groups.

    For each configured stage, produces:
    - An aws_apigatewayv2_stage resource with auto_deploy, stage_variables,
      default_route_settings (throttling, data trace, detailed metrics, logging level),
      route_settings (per-route throttling), and access_log_settings when logging is enabled.
    - An aws_cloudwatch_log_group resource when access logging is enabled.

    When no stages are configured, generates a single $default stage with auto_deploy=true.
    Also uses top-level TerraformField stage fields (access_log_destination_arn,
    default_route_data_trace_enabled, default_route_detailed_metrics_enabled,
    default_route_logging_level, default_route_throttling_burst_limit,
    default_route_throttling_rate_limit) when the stage dict doesn't override them.
    """
    stages = getattr(config, "stages", None)

    # Default log format per requirement 6.4
    default_log_format = (
        '{"requestId":"$context.requestId",'
        '"ip":"$context.identity.sourceIp",'
        '"requestTime":"$context.requestTime",'
        '"httpMethod":"$context.httpMethod",'
        '"routeKey":"$context.routeKey",'
        '"status":"$context.status",'
        '"protocol":"$context.protocol"}'
    )

    # If no stages configured, generate a single $default stage with auto_deploy
    if not stages:
        stages = [{"name": "$default", "auto_deploy": True}]

    parts: list[str] = []

    for stage_cfg in stages:
        stage_name = stage_cfg.get("name", "$default")
        sanitized_name = sanitize_route_name(stage_name)
        resource_name = f"{instance.name}_{sanitized_name}_stage"

        attrs: dict = {
            "api_id": Expr(f"aws_apigatewayv2_api.{instance.name}.id"),
            "name": stage_name,
        }

        # auto_deploy
        auto_deploy = stage_cfg.get("auto_deploy", False)
        if auto_deploy:
            attrs["auto_deploy"] = True

        # stage_variables block
        stage_variables = stage_cfg.get("stage_variables")
        if stage_variables:
            attrs["stage_variables"] = stage_variables

        # default_route_settings block (throttling + data trace + detailed metrics + logging level)
        throttling_burst = stage_cfg.get("throttling_burst_limit")
        throttling_rate = stage_cfg.get("throttling_rate_limit")
        data_trace = stage_cfg.get("data_trace_enabled")
        detailed_metrics = stage_cfg.get("detailed_metrics_enabled")
        logging_level = stage_cfg.get("logging_level")

        # Fall back to top-level TerraformField values from config
        if throttling_burst is None:
            throttling_burst = getattr(
                config, "default_route_throttling_burst_limit", None
            )
        if throttling_rate is None:
            throttling_rate = getattr(
                config, "default_route_throttling_rate_limit", None
            )
        if data_trace is None:
            data_trace = getattr(config, "default_route_data_trace_enabled", None)
        if detailed_metrics is None:
            detailed_metrics = getattr(
                config, "default_route_detailed_metrics_enabled", None
            )
        if logging_level is None:
            logging_level = getattr(config, "default_route_logging_level", None)

        if any(
            v is not None
            for v in [
                throttling_burst,
                throttling_rate,
                data_trace,
                detailed_metrics,
                logging_level,
            ]
        ):
            default_route_settings: dict = {}
            if throttling_burst is not None:
                default_route_settings["throttling_burst_limit"] = throttling_burst
            if throttling_rate is not None:
                default_route_settings["throttling_rate_limit"] = throttling_rate
            if data_trace is not None:
                default_route_settings["data_trace_enabled"] = data_trace
            if detailed_metrics is not None:
                default_route_settings["detailed_metrics_enabled"] = detailed_metrics
            if logging_level is not None:
                default_route_settings["logging_level"] = logging_level
            attrs["default_route_settings"] = default_route_settings

        # route_settings blocks for per-route throttling
        route_throttling = stage_cfg.get("route_throttling")
        if route_throttling:
            route_settings_list = []
            for rt in route_throttling:
                route_key = rt.get("route_key", "$default")
                rs_attrs: dict = {"route_key": route_key}
                if "burst" in rt:
                    rs_attrs["throttling_burst_limit"] = rt["burst"]
                if "rate" in rt:
                    rs_attrs["throttling_rate_limit"] = rt["rate"]
                route_settings_list.append(rs_attrs)
            attrs["route_settings"] = route_settings_list

        # access_log_settings block — from stage dict or top-level config field
        access_logging_enabled = stage_cfg.get("access_logging_enabled", False)
        access_log_dest_arn = stage_cfg.get("access_log_destination_arn")
        if access_log_dest_arn is None:
            access_log_dest_arn = getattr(config, "access_log_destination_arn", None)

        if access_logging_enabled or access_log_dest_arn is not None:
            log_format = stage_cfg.get("access_log_format")
            if log_format is None:
                log_format = getattr(config, "access_log_format", None)
            if log_format is None:
                log_format = default_log_format

            if access_log_dest_arn is not None:
                # Use the explicit destination ARN from config
                attrs["access_log_settings"] = {
                    "destination_arn": Expr("var.access_log_destination_arn"),
                    "format": log_format,
                }
            else:
                # Generate a CloudWatch log group reference
                log_group_resource_name = f"{instance.name}_{sanitized_name}_log_group"
                attrs["access_log_settings"] = {
                    "destination_arn": Expr(
                        f"aws_cloudwatch_log_group.{log_group_resource_name}.arn"
                    ),
                    "format": log_format,
                }

        parts.append(r.render_resource("aws_apigatewayv2_stage", resource_name, attrs))

        # Generate CloudWatch log group when access logging is enabled via stage dict
        # (not when using explicit access_log_destination_arn)
        if access_logging_enabled and access_log_dest_arn is None:
            log_group_resource_name = f"{instance.name}_{sanitized_name}_log_group"
            retention_days = stage_cfg.get("access_log_retention_days", 30)
            log_group_attrs: dict = {
                "name": f"/aws/apigateway/{instance.name}/{sanitized_name}",
                "retention_in_days": retention_days,
            }
            parts.append(
                r.render_resource(
                    "aws_cloudwatch_log_group",
                    log_group_resource_name,
                    log_group_attrs,
                )
            )

    return "\n".join(parts)


def render_variables(config: ApiGatewayConfig, r: HCLRenderer) -> list[str]:
    """Variable blocks this concern contributes."""
    parts: list[str] = []
    # ─── Stages fields ────────────────────────────────────────────────────
    if config.access_log_destination_arn is not None:
        parts.append(
            r.render_variable(
                "access_log_destination_arn",
                "string",
                "ARN of the CloudWatch log group for access logging",
                default=config.access_log_destination_arn,
            )
        )
    if config.access_log_format is not None:
        parts.append(
            r.render_variable(
                "access_log_format",
                "string",
                "Access log format string for the stage",
                default=config.access_log_format,
            )
        )
    if config.default_route_data_trace_enabled is not None:
        parts.append(
            r.render_variable(
                "default_route_data_trace_enabled",
                "bool",
                "Whether data trace logging is enabled for the default route",
                default=config.default_route_data_trace_enabled,
            )
        )
    if config.default_route_detailed_metrics_enabled is not None:
        parts.append(
            r.render_variable(
                "default_route_detailed_metrics_enabled",
                "bool",
                "Whether detailed metrics are enabled for the default route",
                default=config.default_route_detailed_metrics_enabled,
            )
        )
    if config.default_route_logging_level is not None:
        parts.append(
            r.render_variable(
                "default_route_logging_level",
                "string",
                "Logging level for the default route",
                default=config.default_route_logging_level,
            )
        )
    if config.default_route_throttling_burst_limit is not None:
        parts.append(
            r.render_variable(
                "default_route_throttling_burst_limit",
                "number",
                "Throttling burst limit for the default route",
                default=config.default_route_throttling_burst_limit,
            )
        )
    if config.default_route_throttling_rate_limit is not None:
        parts.append(
            r.render_variable(
                "default_route_throttling_rate_limit",
                "number",
                "Throttling rate limit for the default route",
                default=config.default_route_throttling_rate_limit,
            )
        )
    return parts
