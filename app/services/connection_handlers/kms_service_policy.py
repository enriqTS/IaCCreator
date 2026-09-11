"""One aggregated service policy per managed key, with no resource back-references."""

from app.generators.hcl_renderer import Expr
from app.models.ir_models import ConnectionContribution, ModuleInput, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.kms_identities import identity
from app.services.connection_handlers.kms_policy_rules import POLICY_RULES


def needs_service_policy(key: str, project: ProjectIR) -> bool:
    return any(rule.members(key, project) for rule in POLICY_RULES)


class KmsServicePolicy(BaseConnectionHandler):
    def build(self, key: str, project: ProjectIR) -> ConnectionContribution:
        result = ConnectionContribution()
        statements = [
            {
                "Sid": "EnableAccountPermissions",
                "Effect": "Allow",
                "Principal": {
                    "AWS": Expr(
                        '"arn:${data.aws_partition.kms_policy.partition}:iam::${data.aws_caller_identity.kms_policy.account_id}:root"'
                    )
                },
                "Action": "kms:*",
                "Resource": "*",
            }
        ]
        for rule in POLICY_RULES:
            names = rule.members(key, project)
            if not names:
                continue
            arns = Expr("null")
            if rule.variable is not None:
                references = []
                for name in sorted(names):
                    reference, contribution = identity(
                        self._find_instance(name, project)
                    )
                    result.merge(contribution)
                    references.append(reference)
                result.inputs.append(
                    ModuleInput(
                        module=key,
                        name=rule.variable,
                        type="list(string)",
                        value="[" + ", ".join(references) + "]",
                        description="Identities authorized by the key policy",
                    )
                )
                arns = Expr("var." + rule.variable)
            for statement in rule.statements(arns):
                if statement not in statements:
                    statements.append(statement)
        content = 'data "aws_partition" "kms_policy" {}\ndata "aws_region" "kms_policy" {}\ndata "aws_caller_identity" "kms_policy" {}\n'
        content += self._renderer.render_resource(
            "aws_kms_key_policy",
            "services",
            {
                "key_id": Expr(f"aws_kms_key.{key}.arn"),
                "policy": self._renderer.render_json_policy(
                    {"Version": "2012-10-17", "Statement": statements}
                ),
            },
        )
        content += "\nmoved {\n  from = aws_kms_key_policy.cloudtrail\n  to = aws_kms_key_policy.services\n}\n"
        result.resources.append(self._resource(key, "key_policy.tf", content))
        result.outputs.append(
            self._output(
                key,
                "service_key_arn",
                "aws_kms_key_policy.services.key_id",
                "Key ARN available after service permissions are installed",
            )
        )
        if any(item.name == "cloudtrail_arns" for item in result.inputs):
            result.outputs.append(
                self._output(
                    key,
                    "cloudtrail_key_arn",
                    "aws_kms_key_policy.services.key_id",
                    "Policy-ready CloudTrail key ARN",
                )
            )
        return result
