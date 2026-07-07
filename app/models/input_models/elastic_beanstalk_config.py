"""Elastic Beanstalk-specific configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class ElasticBeanstalkConfig(BaseServiceConfig):
    """Elastic Beanstalk-specific configuration."""

    service_type: Literal[ServiceType.ELASTIC_BEANSTALK] = ServiceType.ELASTIC_BEANSTALK
    eb_solution_stack_name: str | None = None
    eb_tier: str | None = None
