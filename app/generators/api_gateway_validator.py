"""Validator for API Gateway configurations.

Validates API Gateway config before HCL generation,
checking routes, stages, authorizers, domains, VPC links,
integrations, and throttling settings.
"""

import re

from app.models.api_gateway_models import ValidationError
from app.models.input_models._base import BaseServiceConfig
from app.models.ir_models import ResourceInstanceIR

# Allowed HTTP methods for API Gateway routes
ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "ANY"}

# Regex pattern for valid route paths (allows greedy path variables like {proxy+})
PATH_PATTERN = re.compile(r"^/[a-zA-Z0-9\-_./{}+]*$")


class APIGatewayValidator:
    """Validates API Gateway configuration before generation."""

    def validate(self, instance: ResourceInstanceIR) -> list[ValidationError]:
        """Run all validation rules and return errors.

        Args:
            instance: The resource instance IR containing the API Gateway config.

        Returns:
            A list of ValidationError objects. Empty list means valid config.
        """
        config = instance.config
        errors: list[ValidationError] = []

        errors.extend(self._validate_routes(config))
        errors.extend(self._validate_stages(config))
        errors.extend(self._validate_authorizers(config))
        errors.extend(self._validate_domain(config))
        errors.extend(self._validate_vpc_links(config))
        errors.extend(self._validate_integrations(config))
        errors.extend(self._validate_throttling(config))

        return errors

    def _validate_routes(self, config: BaseServiceConfig) -> list[ValidationError]:
        """Validate route configurations.

        Checks:
        - Method is in the allowed set
        - Path matches the required pattern
        - No duplicate route_keys
        """
        errors: list[ValidationError] = []
        routes = getattr(config, "routes", None)
        if not routes:
            return errors

        seen_route_keys: set[str] = set()

        for i, route in enumerate(routes):
            methods = route.get("methods", [])
            path = route.get("path", "")

            # Validate methods
            if not isinstance(methods, list) or not methods:
                errors.append(
                    ValidationError(
                        field=f"routes[{i}].methods",
                        message="Route must have a non-empty 'methods' array.",
                        code="INVALID_METHOD",
                    )
                )
            else:
                for method in methods:
                    if method.upper() not in ALLOWED_METHODS:
                        errors.append(
                            ValidationError(
                                field=f"routes[{i}].methods",
                                message=(
                                    f"Invalid HTTP method '{method}'. "
                                    f"Allowed methods: {', '.join(sorted(ALLOWED_METHODS))}"
                                ),
                                code="INVALID_METHOD",
                            )
                        )

            # Validate path
            if not PATH_PATTERN.match(path):
                errors.append(
                    ValidationError(
                        field=f"routes[{i}].path",
                        message=(
                            f"Invalid route path '{path}'. "
                            "Path must start with '/' and contain only "
                            "alphanumeric characters, hyphens, underscores, "
                            "periods, forward slashes, curly braces, and '+'."
                        ),
                        code="INVALID_PATH",
                    )
                )

            # Check for duplicate route_keys
            if isinstance(methods, list):
                for method in methods:
                    route_key = f"{method.upper()} {path}"
                    if route_key in seen_route_keys:
                        errors.append(
                            ValidationError(
                                field=f"routes[{i}]",
                                message=f"Duplicate route_key '{route_key}'.",
                                code="DUPLICATE_ROUTE",
                            )
                        )
                    else:
                        seen_route_keys.add(route_key)

        # Validate authorizer references on routes
        defined_authorizers: set[str] = set()
        if getattr(config, "authorizers", None):
            for auth in getattr(config, "authorizers", []):
                name = auth.get("name", "")
                if name:
                    defined_authorizers.add(name)

        for i, route in enumerate(routes):
            authorizer_name = route.get("authorizer_name")
            if authorizer_name and authorizer_name not in defined_authorizers:
                errors.append(
                    ValidationError(
                        field=f"routes[{i}].authorizer_name",
                        message=(
                            f"Route references undefined authorizer '{authorizer_name}'."
                        ),
                        code="UNDEFINED_AUTHORIZER",
                    )
                )

        return errors

    def _validate_stages(self, config: BaseServiceConfig) -> list[ValidationError]:
        """Validate stage configurations.

        Checks:
        - Stage variables max 50 entries
        - No empty keys or values in stage_variables
        """
        errors: list[ValidationError] = []
        stages = getattr(config, "stages", None)
        if not stages:
            return errors

        for i, stage in enumerate(stages):
            stage_variables = stage.get("stage_variables")
            if stage_variables is None:
                continue

            # Check max 50 entries
            if len(stage_variables) > 50:
                errors.append(
                    ValidationError(
                        field=f"stages[{i}].stage_variables",
                        message=(
                            f"Stage variables exceed maximum of 50 entries "
                            f"(has {len(stage_variables)})."
                        ),
                        code="STAGE_VARIABLES_LIMIT",
                    )
                )

            # Check for empty keys or values
            for key, value in stage_variables.items():
                if not key or not value:
                    errors.append(
                        ValidationError(
                            field=f"stages[{i}].stage_variables",
                            message=(
                                "Stage variables must not contain empty keys or values."
                            ),
                            code="INVALID_STAGE_VARIABLES",
                        )
                    )
                    break  # One error per stage is sufficient

        return errors

    def _validate_authorizers(self, config: BaseServiceConfig) -> list[ValidationError]:
        """Validate authorizer configurations.

        Checks:
        - JWT/Cognito authorizers require issuer and audience
        - payload_format_version must be "1.0" or "2.0"
        """
        errors: list[ValidationError] = []
        authorizers = getattr(config, "authorizers", None)
        if not authorizers:
            return errors

        for i, auth in enumerate(authorizers):
            auth_type = auth.get("type", "")

            # JWT and Cognito require issuer + audience
            if auth_type in ("JWT", "COGNITO_USER_POOLS"):
                issuer = auth.get("issuer")
                audience = auth.get("audience")

                if not issuer:
                    errors.append(
                        ValidationError(
                            field=f"authorizers[{i}].issuer",
                            message=(
                                f"{auth_type} authorizer requires an 'issuer' URL."
                            ),
                            code="MISSING_ISSUER",
                        )
                    )

                if not audience:
                    errors.append(
                        ValidationError(
                            field=f"authorizers[{i}].audience",
                            message=(
                                f"{auth_type} authorizer requires at least one "
                                "'audience' value."
                            ),
                            code="MISSING_AUDIENCE",
                        )
                    )

            # Validate payload_format_version for Lambda authorizers
            payload_version = auth.get("payload_format_version")
            if payload_version is not None and payload_version not in ("1.0", "2.0"):
                errors.append(
                    ValidationError(
                        field=f"authorizers[{i}].payload_format_version",
                        message=(
                            f"Invalid payload_format_version '{payload_version}'. "
                            "Must be '1.0' or '2.0'."
                        ),
                        code="INVALID_PAYLOAD_VERSION",
                    )
                )

        return errors

    def _validate_domain(self, config: BaseServiceConfig) -> list[ValidationError]:
        """Validate custom domain configuration.

        Checks:
        - custom_domain requires certificate_arn
        """
        errors: list[ValidationError] = []
        domain = getattr(config, "custom_domain", None)
        if not domain:
            return errors

        certificate_arn = domain.get("certificate_arn")
        if not certificate_arn:
            errors.append(
                ValidationError(
                    field="custom_domain.certificate_arn",
                    message=("Custom domain requires a valid ACM certificate ARN."),
                    code="MISSING_CERTIFICATE",
                )
            )

        return errors

    def _validate_vpc_links(self, config: BaseServiceConfig) -> list[ValidationError]:
        """Validate VPC link configurations.

        Checks:
        - At least 1 subnet_id required
        - 1-3 subnets allowed
        - 1-5 security groups allowed
        """
        errors: list[ValidationError] = []
        vpc_links = getattr(config, "vpc_links", None)
        if not vpc_links:
            return errors

        for i, vpc_link in enumerate(vpc_links):
            subnet_ids = vpc_link.get("subnet_ids", [])
            security_group_ids = vpc_link.get("security_group_ids", [])

            # Require at least 1 subnet
            if not subnet_ids:
                errors.append(
                    ValidationError(
                        field=f"vpc_links[{i}].subnet_ids",
                        message="VPC link requires at least 1 subnet ID.",
                        code="EMPTY_SUBNETS",
                    )
                )
            elif len(subnet_ids) > 3:
                errors.append(
                    ValidationError(
                        field=f"vpc_links[{i}].subnet_ids",
                        message=(
                            f"VPC link allows 1-3 subnet IDs (has {len(subnet_ids)})."
                        ),
                        code="EMPTY_SUBNETS",
                    )
                )

            # Validate security groups (1-5)
            if not security_group_ids:
                errors.append(
                    ValidationError(
                        field=f"vpc_links[{i}].security_group_ids",
                        message="VPC link requires at least 1 security group ID.",
                        code="EMPTY_SUBNETS",
                    )
                )
            elif len(security_group_ids) > 5:
                errors.append(
                    ValidationError(
                        field=f"vpc_links[{i}].security_group_ids",
                        message=(
                            f"VPC link allows 1-5 security group IDs "
                            f"(has {len(security_group_ids)})."
                        ),
                        code="EMPTY_SUBNETS",
                    )
                )

        return errors

    def _validate_integrations(self, config: BaseServiceConfig) -> list[ValidationError]:
        """Validate integration configurations.

        Checks:
        - HTTP/HTTP_PROXY integrations require URI
        - VPC_LINK integrations require connection_id (vpc_link_name)
        - VPC link references must be defined
        """
        errors: list[ValidationError] = []
        integrations = getattr(config, "integrations", None)
        if not integrations:
            return errors

        # Build set of defined VPC link names
        defined_vpc_links: set[str] = set()
        if getattr(config, "vpc_links", None):
            for vpc_link in getattr(config, "vpc_links", []):
                name = vpc_link.get("name", "")
                if name:
                    defined_vpc_links.add(name)

        for i, integration in enumerate(integrations):
            integration_type = integration.get("type", "")
            uri = integration.get("uri")
            vpc_link_name = integration.get("vpc_link_name")

            # HTTP and HTTP_PROXY require URI
            if integration_type in ("HTTP", "HTTP_PROXY") and not uri:
                errors.append(
                    ValidationError(
                        field=f"integrations[{i}].uri",
                        message=(
                            f"{integration_type} integration requires "
                            "an 'integration_uri'."
                        ),
                        code="MISSING_INTEGRATION_URI",
                    )
                )

            # VPC_LINK requires connection_id (vpc_link_name)
            if integration_type == "VPC_LINK" and not vpc_link_name:
                errors.append(
                    ValidationError(
                        field=f"integrations[{i}].vpc_link_name",
                        message="VPC_LINK integration requires a 'connection_id'.",
                        code="MISSING_CONNECTION_ID",
                    )
                )

            # Check undefined VPC link references
            if vpc_link_name and vpc_link_name not in defined_vpc_links:
                errors.append(
                    ValidationError(
                        field=f"integrations[{i}].vpc_link_name",
                        message=(
                            f"Integration references undefined VPC link "
                            f"'{vpc_link_name}'."
                        ),
                        code="UNDEFINED_VPC_LINK",
                    )
                )

        return errors

    def _validate_throttling(self, config: BaseServiceConfig) -> list[ValidationError]:
        """Validate throttling configuration.

        Checks:
        - burst_limit: 1–5000
        - rate_limit: 1.0–10000.0
        """
        errors: list[ValidationError] = []

        burst = getattr(config, "throttling_burst_limit", None)
        rate = getattr(config, "throttling_rate_limit", None)

        if burst is not None and (burst < 1 or burst > 5000):
            errors.append(
                ValidationError(
                    field="throttling_burst_limit",
                    message=(
                        f"Throttling burst limit must be between 1 and 5000 "
                        f"(got {burst})."
                    ),
                    code="THROTTLE_OUT_OF_RANGE",
                )
            )

        if rate is not None and (rate < 1.0 or rate > 10000.0):
            errors.append(
                ValidationError(
                    field="throttling_rate_limit",
                    message=(
                        f"Throttling rate limit must be between 1.0 and 10000.0 "
                        f"(got {rate})."
                    ),
                    code="THROTTLE_OUT_OF_RANGE",
                )
            )

        return errors
