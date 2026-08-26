"""AWS Backup vault and plan configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField, ValidationRule


class BackupConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.BACKUP] = ServiceType.BACKUP
    vault_name: str = TerraformField("backup-vault", description="Backup vault name")
    kms_key_arn: str | None = TerraformField(
        None, description="KMS key ARN for vault encryption"
    )
    plan_name: str = TerraformField("backup-plan", description="Backup plan name")
    schedule: str = TerraformField(
        "cron(0 5 ? * * *)", description="EventBridge cron schedule"
    )
    start_window: int = TerraformField(
        60, description="Start window in minutes", validation=ValidationRule(min=60)
    )
    completion_window: int = TerraformField(
        180,
        description="Completion window in minutes",
        validation=ValidationRule(min=60),
    )
    delete_after_days: int = TerraformField(
        35,
        description="Days before recovery point deletion",
        validation=ValidationRule(min=1),
    )
