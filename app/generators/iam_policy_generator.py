"""IAM Policy Generator — produces JSON IAM policy documents for Lambda resource instances."""

import json

from app.models.ir_models import ResourceInstanceIR


# Base CloudWatch Logs permissions every Lambda needs
_BASE_LOG_ACTIONS = [
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents",
]


class IAMPolicyGenerator:
    """Generates standalone JSON IAM policy documents.

    Each Lambda resource instance gets a single consolidated policy file
    containing both the base execution policy (CloudWatch Logs) and any
    connection-derived permission statements.
    """

    def generate_policy_document(self, instance: ResourceInstanceIR) -> str:
        """Produce a complete JSON IAM policy for a Lambda resource instance.

        Consolidates the base execution policy with all connection-derived
        IAM statements into a single document.
        """
        statements = []

        # Base execution policy — CloudWatch Logs
        statements.append({
            "Effect": "Allow",
            "Action": _BASE_LOG_ACTIONS,
            "Resource": f"arn:aws:logs:*:*:log-group:/aws/lambda/{instance.name}:*",
        })

        # Connection-derived statements
        for iam_stmt in instance.iam_statements:
            stmt: dict = {
                "Effect": iam_stmt.effect,
                "Action": iam_stmt.actions,
            }
            if len(iam_stmt.resources) == 1:
                stmt["Resource"] = iam_stmt.resources[0]
            else:
                stmt["Resource"] = iam_stmt.resources
            statements.append(stmt)

        policy = {
            "Version": "2012-10-17",
            "Statement": statements,
        }
        return json.dumps(policy, indent=2) + "\n"

    def generate_base_execution_policy(self, function_name: str) -> str:
        """Produce a JSON IAM policy with only CloudWatch Logs permissions."""
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": _BASE_LOG_ACTIONS,
                    "Resource": f"arn:aws:logs:*:*:log-group:/aws/lambda/{function_name}:*",
                }
            ],
        }
        return json.dumps(policy, indent=2) + "\n"
