"""Aggregate bucket notifications under one Terraform resource owner."""

from app.generators.hcl_renderer import Expr
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier
from app.services.connection_handlers.s3_notification_rules import (
    notification_key,
    validate_notification_filters,
)


class S3Notifications(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        peers = [
            item
            for item in project.connections
            if item.source_name == connection.source_name
            and item.source_service == ServiceType.S3
            and item.connection_type == "notifies"
        ]
        bucket = connection.source_name
        attrs: dict = {"bucket": Expr(f"aws_s3_bucket.{bucket}.id")}
        dependencies = set()
        unique = {notification_key(item): item for item in peers}
        validate_notification_filters(list(unique.values()))
        for key in sorted(unique):
            item = unique[key]
            prefix = safe_identifier(item.target_name)
            block_name, arn_field, suffix = {
                ServiceType.LAMBDA: (
                    "lambda_function",
                    "lambda_function_arn",
                    "function_arn",
                ),
                ServiceType.SNS: ("topic", "topic_arn", "notification_arn"),
                ServiceType.SQS: ("queue", "queue_arn", "notification_arn"),
            }[item.target_service]
            block = {
                arn_field: Expr(f"var.{prefix}_{suffix}"),
                "events": sorted(
                    set(item.connection_config.get("events") or ["s3:ObjectCreated:*"])
                ),
            }
            for name in ("filter_prefix", "filter_suffix"):
                if item.connection_config.get(name):
                    block[name] = item.connection_config[name]
            attrs.setdefault(block_name, []).append(block)
            if item.target_service == ServiceType.LAMBDA:
                dependencies.add(f"aws_lambda_permission.{prefix}_permission")
        instance = self._find_instance(bucket, project)
        for service, block_name, arn_field in (
            ("lambda", "lambda_function", "lambda_function_arn"),
            ("sqs", "queue", "queue_arn"),
            ("sns", "topic", "topic_arn"),
        ):
            if getattr(instance.config, f"notification_{service}_arn", None):
                attrs.setdefault(block_name, []).append(
                    {
                        arn_field: Expr(f"var.notification_{service}_arn"),
                        "events": Expr(f"var.notification_{service}_events")
                        if getattr(
                            instance.config, f"notification_{service}_events", None
                        )
                        else ["s3:ObjectCreated:*"],
                    }
                )
        if dependencies:
            attrs["depends_on"] = Expr("[" + ", ".join(sorted(dependencies)) + "]")
        return ConnectionContribution(
            resources=[
                self._resource(
                    bucket,
                    "notifications.tf",
                    self._renderer.render_resource(
                        "aws_s3_bucket_notification",
                        f"{safe_identifier(bucket)}_notification",
                        attrs,
                    ),
                )
            ]
        )
