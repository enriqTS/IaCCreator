"""IAM Policy Generator — produces JSON policy documents for role-owning resources."""

import json

from app.models.ir_models import ResourceInstanceIR


class IAMPolicyGenerator:
    """Generates the standalone JSON policy document attached to an execution role."""

    def generate_policy_document(self, instance: ResourceInstanceIR) -> str:
        """Consolidate the service's base statements with every connection grant."""
        config_cls = type(instance.config)
        statements: list[dict] = list(
            config_cls.execution_role_base_statements(instance.name)
        )

        for iam_stmt in instance.iam_statements:
            statement: dict = {"Effect": iam_stmt.effect, "Action": iam_stmt.actions}
            if len(iam_stmt.resources) == 1:
                statement["Resource"] = iam_stmt.resources[0]
            else:
                statement["Resource"] = iam_stmt.resources
            statements.append(statement)

        return (
            json.dumps({"Version": "2012-10-17", "Statement": statements}, indent=2)
            + "\n"
        )
