"""Serverless Valkey and Redis configuration with externally managed user groups."""

from typing import Literal

from pydantic import PrivateAttr

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import OptionEntry, TerraformField


class ElastiCacheServerlessConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.ELASTICACHE_SERVERLESS] = (
        ServiceType.ELASTICACHE_SERVERLESS
    )
    _iam_client_access: bool = PrivateAttr(default=False)
    cache_name: str = TerraformField(
        "serverless-cache", description="Serverless cache name"
    )
    engine: Literal["valkey", "redis"] = TerraformField(
        "valkey",
        description="Cache engine",
        options=[
            OptionEntry(value="valkey", label="Valkey"),
            OptionEntry(value="redis", label="Redis OSS"),
        ],
    )
    user_group_id: str | None = TerraformField(
        None, description="Existing user group containing the selected IAM users"
    )
    subnet_ids: list[str] = TerraformField(
        [], description="Existing VPC subnets for cache endpoints"
    )
    security_group_ids: list[str] = TerraformField(
        [], description="VPC security groups for cache endpoints"
    )
