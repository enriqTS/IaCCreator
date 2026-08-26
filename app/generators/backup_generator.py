"""Terraform generator for AWS Backup vaults and plans."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.backup_config import BackupConfig
from app.models.ir_models import ResourceInstanceIR


class BackupGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, BackupConfig)
        vault_attrs = {"name": Expr("var.vault_name")}
        if config.kms_key_arn is not None:
            vault_attrs["kms_key_arn"] = Expr("var.kms_key_arn")
        vault = self._r.render_resource("aws_backup_vault", instance.name, vault_attrs)
        plan = self._r.render_resource(
            "aws_backup_plan",
            instance.name,
            {
                "name": Expr("var.plan_name"),
                "rule": [
                    {
                        "rule_name": f"{instance.name}-rule",
                        "target_vault_name": Expr(
                            f"aws_backup_vault.{instance.name}.name"
                        ),
                        "schedule": Expr("var.schedule"),
                        "start_window": Expr("var.start_window"),
                        "completion_window": Expr("var.completion_window"),
                        "lifecycle": {"delete_after": Expr("var.delete_after_days")},
                    }
                ],
            },
        )
        return vault + plan

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, BackupConfig)
        fields = [
            ("vault_name", "string", "Backup vault name"),
            ("plan_name", "string", "Backup plan name"),
            ("schedule", "string", "Backup schedule"),
            ("start_window", "number", "Start window in minutes"),
            ("completion_window", "number", "Completion window in minutes"),
            ("delete_after_days", "number", "Recovery point retention in days"),
        ]
        if config.kms_key_arn is not None:
            fields.append(("kms_key_arn", "string", "Vault KMS key ARN"))
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        vault = f"aws_backup_vault.{instance.name}"
        plan = f"aws_backup_plan.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("vault_arn", f"{vault}.arn", "Backup vault ARN"),
                self._r.render_output("plan_id", f"{plan}.id", "Backup plan ID"),
                self._r.render_output("plan_arn", f"{plan}.arn", "Backup plan ARN"),
            ]
        )
