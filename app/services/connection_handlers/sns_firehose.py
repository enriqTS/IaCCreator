"""SNS subscribes a generated Firehose stream with a stream-scoped role."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.sns_firehose import SnsFirehoseConfig
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier


class SnsFirehoseHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        config = SnsFirehoseConfig.model_validate(connection.connection_config)
        topic, stream = connection.source_name, connection.target_name
        source = self._find_instance(topic, project)
        if source.config.fifo_topic:
            raise InvalidConnectionConfigError(
                topic,
                stream,
                connection.connection_type,
                [
                    {
                        "loc": ("fifo_topic",),
                        "msg": "Firehose requires a standard SNS topic",
                    }
                ],
            )
        identifier = safe_identifier(topic)
        topic_var = f"{identifier}_topic_arn"
        role = f"{identifier}_sns_delivery"
        render = self._renderer.render_resource
        policy = self._renderer.render_json_policy
        resources = [
            render(
                "aws_iam_role",
                role,
                {
                    "name_prefix": "sns-firehose-",
                    "assume_role_policy": policy(
                        {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Principal": {"Service": "sns.amazonaws.com"},
                                    "Action": "sts:AssumeRole",
                                }
                            ],
                        }
                    ),
                },
            ),
            render(
                "aws_iam_role_policy",
                role,
                {
                    "role": Expr(f"aws_iam_role.{role}.id"),
                    "policy": policy(
                        {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Action": [
                                        "firehose:PutRecord",
                                        "firehose:PutRecordBatch",
                                    ],
                                    "Resource": [
                                        Expr(
                                            f"aws_kinesis_firehose_delivery_stream.{stream}.arn"
                                        )
                                    ],
                                }
                            ],
                        }
                    ),
                },
            ),
            render(
                "aws_sns_topic_subscription",
                f"{identifier}_firehose",
                {
                    "topic_arn": Expr(f"var.{topic_var}"),
                    "protocol": "firehose",
                    "endpoint": Expr(
                        f"aws_kinesis_firehose_delivery_stream.{stream}.arn"
                    ),
                    "subscription_role_arn": Expr(f"aws_iam_role.{role}.arn"),
                    "raw_message_delivery": config.raw_message_delivery,
                    "depends_on": Expr(f"[aws_iam_role_policy.{role}]"),
                    "lifecycle": {
                        "precondition": [
                            {
                                "condition": Expr(
                                    f'!endswith(var.{topic_var}, ".fifo")'
                                ),
                                "error_message": "Firehose requires a standard SNS topic.",
                            }
                        ]
                    },
                },
            ),
        ]
        return ConnectionContribution(
            inputs=[
                self._input(
                    stream,
                    topic,
                    "topic_arn",
                    f"module.{topic}.topic_arn",
                    "ARN of the publishing SNS topic",
                )
            ],
            resources=[
                self._resource(stream, f"subscription_{topic}.tf", "\n".join(resources))
            ],
        )
