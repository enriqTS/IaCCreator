"""Unit tests for EKSGenerator.

Requirements: 6.1–6.6
"""

import pytest

from app.generators.eks_generator import EKSGenerator
from app.models.input_models import ServiceType
from app.models.input_models.eks_config import EksConfig
from app.models.ir_models import ResourceInstanceIR


def _make_eks_instance(
    name: str = "my-cluster",
    **config_kwargs,
) -> ResourceInstanceIR:
    """Create a minimal ResourceInstanceIR for EKS."""
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.EKS,
        config=EksConfig(**config_kwargs),
    )


@pytest.fixture
def gen() -> EKSGenerator:
    return EKSGenerator()


# ---------------------------------------------------------------------------
# Minimal config tests
# ---------------------------------------------------------------------------


class TestEKSGeneratorMinimal:
    """Test EKSGenerator with minimal config (all optional fields None)."""

    def test_resource_tf_contains_eks_cluster(self, gen: EKSGenerator):
        instance = _make_eks_instance()
        result = gen.generate_resource_tf(instance)
        assert "aws_eks_cluster" in result

    def test_resource_tf_references_cluster_name_variable(self, gen: EKSGenerator):
        instance = _make_eks_instance()
        result = gen.generate_resource_tf(instance)
        assert "var.cluster_name" in result

    def test_resource_tf_references_cluster_role_arn_variable(self, gen: EKSGenerator):
        instance = _make_eks_instance()
        result = gen.generate_resource_tf(instance)
        assert "var.cluster_role_arn" in result

    def test_variables_tf_contains_required_variables(self, gen: EKSGenerator):
        instance = _make_eks_instance()
        result = gen.generate_variables_tf(instance)
        assert "cluster_name" in result
        assert "cluster_role_arn" in result
        assert "subnet_ids" in result

    def test_outputs_tf_contains_cluster_arn(self, gen: EKSGenerator):
        instance = _make_eks_instance()
        result = gen.generate_outputs_tf(instance)
        assert "cluster_arn" in result

    def test_outputs_tf_contains_cluster_endpoint(self, gen: EKSGenerator):
        instance = _make_eks_instance()
        result = gen.generate_outputs_tf(instance)
        assert "cluster_endpoint" in result

    def test_resource_tf_no_version_when_not_set(self, gen: EKSGenerator):
        instance = _make_eks_instance()
        result = gen.generate_resource_tf(instance)
        assert "eks_version" not in result


# ---------------------------------------------------------------------------
# Optional config tests
# ---------------------------------------------------------------------------


class TestEKSGeneratorWithOptionalConfig:
    """Test EKSGenerator with optional config fields set."""

    def test_resource_tf_includes_version(self, gen: EKSGenerator):
        instance = _make_eks_instance(eks_version="1.28")
        result = gen.generate_resource_tf(instance)
        assert "version" in result

    def test_resource_tf_includes_endpoint_public_access(self, gen: EKSGenerator):
        instance = _make_eks_instance(eks_endpoint_public_access=True)
        result = gen.generate_resource_tf(instance)
        assert "endpoint_public_access" in result

    def test_variables_tf_includes_version_variable(self, gen: EKSGenerator):
        instance = _make_eks_instance(eks_version="1.28")
        result = gen.generate_variables_tf(instance)
        assert "eks_version" in result

    def test_variables_tf_includes_endpoint_public_access_variable(
        self, gen: EKSGenerator
    ):
        instance = _make_eks_instance(eks_endpoint_public_access=True)
        result = gen.generate_variables_tf(instance)
        assert "eks_endpoint_public_access" in result
