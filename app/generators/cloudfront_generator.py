"""Terraform generator for CloudFront distributions."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.cloudfront_config import CloudFrontConfig
from app.models.ir_models import ResourceInstanceIR


class CloudFrontGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, CloudFrontConfig)
        attrs = {
            "enabled": Expr("var.enabled"),
            "price_class": Expr("var.price_class"),
            "origin": [
                {
                    "domain_name": Expr("var.origin_domain_name"),
                    "origin_id": Expr("var.origin_id"),
                    "custom_origin_config": {
                        "http_port": 80,
                        "https_port": 443,
                        "origin_protocol_policy": "https-only",
                        "origin_ssl_protocols": ["TLSv1.2"],
                    },
                }
            ],
            "default_cache_behavior": [
                {
                    "allowed_methods": [
                        "DELETE",
                        "GET",
                        "HEAD",
                        "OPTIONS",
                        "PATCH",
                        "POST",
                        "PUT",
                    ],
                    "cached_methods": ["GET", "HEAD"],
                    "target_origin_id": Expr("var.origin_id"),
                    "viewer_protocol_policy": Expr("var.viewer_protocol_policy"),
                    "forwarded_values": {
                        "query_string": False,
                        "cookies": {"forward": "none"},
                    },
                }
            ],
            "restrictions": [
                {"geo_restriction": {"restriction_type": "none", "locations": []}}
            ],
            "viewer_certificate": [{"cloudfront_default_certificate": True}],
        }
        if config.default_root_object is not None:
            attrs["default_root_object"] = Expr("var.default_root_object")
        return self._r.render_resource(
            "aws_cloudfront_distribution", instance.name, attrs
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, CloudFrontConfig)
        parts = [
            self._r.render_variable(
                "origin_domain_name", "string", "Origin DNS domain name"
            ),
            self._r.render_variable("origin_id", "string", "Origin identifier"),
            self._r.render_variable("enabled", "bool", "Enable the distribution"),
            self._r.render_variable(
                "viewer_protocol_policy", "string", "Viewer protocol policy"
            ),
            self._r.render_variable(
                "price_class", "string", "Edge location price class"
            ),
        ]
        if config.default_root_object is not None:
            parts.append(
                self._r.render_variable(
                    "default_root_object", "string", "Default root object"
                )
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        return "\n".join(
            [
                self._r.render_output(
                    "distribution_id",
                    f"aws_cloudfront_distribution.{instance.name}.id",
                    "Distribution ID",
                ),
                self._r.render_output(
                    "distribution_arn",
                    f"aws_cloudfront_distribution.{instance.name}.arn",
                    "Distribution ARN",
                ),
                self._r.render_output(
                    "domain_name",
                    f"aws_cloudfront_distribution.{instance.name}.domain_name",
                    "Distribution domain name",
                ),
            ]
        )
