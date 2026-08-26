"""Terraform generator for AWS CodeArtifact domains and repositories."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.codeartifact_config import CodeArtifactConfig
from app.models.ir_models import ResourceInstanceIR


class CodeArtifactGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, CodeArtifactConfig)
        domain_attrs = {"domain": Expr("var.domain_name")}
        if config.kms_key is not None:
            domain_attrs["encryption_key"] = Expr("var.kms_key")
        domain = self._r.render_resource(
            "aws_codeartifact_domain", instance.name, domain_attrs
        )
        repository_attrs = {
            "repository": Expr("var.repository_name"),
            "domain": Expr(f"aws_codeartifact_domain.{instance.name}.domain"),
        }
        if config.description is not None:
            repository_attrs["description"] = Expr("var.description")
        if config.upstream_repository_names:
            repository_attrs["upstream"] = [
                {"repository_name": Expr(f"var.upstream_repository_names[{index}]")}
                for index in range(len(config.upstream_repository_names))
            ]
        repository = self._r.render_resource(
            "aws_codeartifact_repository", instance.name, repository_attrs
        )
        return domain + repository

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, CodeArtifactConfig)
        fields = [
            ("domain_name", "string", "CodeArtifact domain name"),
            ("repository_name", "string", "CodeArtifact repository name"),
            ("upstream_repository_names", "list(string)", "Upstream repository names"),
        ]
        if config.description is not None:
            fields.append(("description", "string", "Repository description"))
        if config.kms_key is not None:
            fields.append(("kms_key", "string", "Domain KMS key ARN"))
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        domain = f"aws_codeartifact_domain.{instance.name}"
        repository = f"aws_codeartifact_repository.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "domain_arn", f"{domain}.arn", "CodeArtifact domain ARN"
                ),
                self._r.render_output(
                    "repository_arn", f"{repository}.arn", "CodeArtifact repository ARN"
                ),
                self._r.render_output(
                    "repository_name",
                    f"{repository}.repository",
                    "CodeArtifact repository name",
                ),
            ]
        )
