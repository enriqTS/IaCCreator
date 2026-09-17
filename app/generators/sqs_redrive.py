"""Render standalone redrive attachments with native queue compatibility guards."""

from app.generators.hcl_renderer import Expr, HCLRenderer


def render_redrive(source: str, target: str, count: int) -> str:
    renderer = HCLRenderer()
    queue = f"aws_sqs_queue.{target}"
    variable = f"var.redrive_{source}"
    return renderer.render_resource(
        "aws_sqs_queue_redrive_policy",
        f"source_{source}",
        {
            "queue_url": Expr(f"{variable}_url"),
            "redrive_policy": renderer.render_json_policy(
                {
                    "deadLetterTargetArn": Expr(f"{queue}.arn"),
                    "maxReceiveCount": count,
                }
            ),
            "depends_on": Expr(
                "[aws_sqs_queue_redrive_allow_policy.connected_sources]"
            ),
            "lifecycle": {
                "precondition": [
                    {
                        "condition": Expr(
                            f"{variable}_fifo_queue == {queue}.fifo_queue"
                        ),
                        "error_message": "Source and dead-letter queues must have matching FIFO settings.",
                    },
                    {
                        "condition": Expr(
                            f'join(":", slice(split(":", {variable}_arn), 0, 5)) == join(":", slice(split(":", {queue}.arn), 0, 5))'
                        ),
                        "error_message": "Dead-letter queues must share the source account, partition, and region.",
                    },
                ]
            },
        },
    )
