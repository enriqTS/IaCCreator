"""Where an instance module's files live inside the generated project."""

from __future__ import annotations

from app.generators.service_category_map import get_category
from app.models.ir_models import ResourceInstanceIR


def instance_module_dir(root: str, instance: ResourceInstanceIR) -> str:
    """Directory holding one instance module's Terraform files."""
    category = get_category(instance.service_type)
    return f"{root}/modules/{category}/{instance.service_type.value}/{instance.name}"
