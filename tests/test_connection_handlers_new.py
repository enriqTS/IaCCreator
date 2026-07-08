"""Unit tests for all connection handlers in ConnectionProcessor.

Covers task 5.7 of the connection-aware-terraform-generation spec:
- Enhanced _handle_apigw_lambda (integration, route, permission)
- _handle_lambda_sns (IAM statement with sns:Publish)
- _handle_lambda_sqs (IAM statement with sqs:SendMessage)
- _handle_sqs_lambda (event source mapping, permission, IAM)
- _handle_sns_sqs (subscription, queue policy)
- _handle_sns_lambda (subscription, permission)
- Terraform resource reference consistency across all handlers

Requirements: 3.2, 3.3, 3.4, 3.5, 4.1–4.6, 5.1, 5.2, 6.1–6.6,
             7.1–7.4, 8.1–8.4, 9.1, 9.2, 11.1–11.3
"""


from app.models.input_models import ServiceType
from app.models.input_models._base import BaseServiceConfig
from app.models.input_models.api_gateway_config import ApiGatewayConfig
from app.models.input_models.dynamodb_config import DynamoDBConfig
from app.models.input_models.lambda_config import LambdaConfig
from app.models.input_models.s3_config import S3Config
from app.models.input_models.sns_config import SnsConfig
from app.models.input_models.sqs_config import SqsConfig
from app.models.ir_models import (
    ConnectionIR,
    EnvironmentIR,
    GlobalTerraformConfigIR,
    ProjectIR,
    ResourceInstanceIR,
    ServiceModuleIR,
)
from app.services.connection_processor import ConnectionProcessor

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _lambda_ir(name: str = "my-func") -> ResourceInstanceIR:
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.LAMBDA,
        config=LambdaConfig(
            function_name=name, handler="index.handler", runtime="python3.12"
        ),
    )


def _apigw_ir(name: str = "my-api") -> ResourceInstanceIR:
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.API_GATEWAY,
        config=ApiGatewayConfig(api_name=name, protocol_type="HTTP"),
    )


def _sns_ir(name: str = "my-topic") -> ResourceInstanceIR:
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.SNS,
        config=SnsConfig(),
    )


def _sqs_ir(name: str = "my-queue") -> ResourceInstanceIR:
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.SQS,
        config=SqsConfig(),
    )


def _make_project(
    instances: list[ResourceInstanceIR],
    connections: list[ConnectionIR],
    project_name: str = "test-project",
) -> ProjectIR:
    """Build a minimal ProjectIR grouping instances by service type."""
    modules_map: dict[ServiceType, list[ResourceInstanceIR]] = {}
    for inst in instances:
        modules_map.setdefault(inst.service_type, []).append(inst)

    modules = [
        ServiceModuleIR(service_type=svc, instances=insts)
        for svc, insts in modules_map.items()
    ]

    return ProjectIR(
        project_name=project_name,
        environments=[EnvironmentIR(name="dev", variables={}, module_refs=[])],
        modules=modules,
        connections=connections,
        global_config=GlobalTerraformConfigIR(),
    )


# ===========================================================================
# 1. Enhanced _handle_apigw_lambda
# ===========================================================================


class TestHandleApigwLambda:
    """Test enhanced API Gateway → Lambda handler generates integration, route, and permission."""

    def setup_method(self):
        self.processor = ConnectionProcessor()

    def _process_apigw_lambda(self, connection_config=None):
        """Helper: create APIGW→Lambda connection and process it."""
        apigw = _apigw_ir("my-api")
        func = _lambda_ir("my-func")
        conn = ConnectionIR(
            source_name="my-api",
            target_name="my-func",
            source_service=ServiceType.API_GATEWAY,
            target_service=ServiceType.LAMBDA,
            connection_type="triggers",
            connection_config=connection_config or {},
        )
        project = _make_project([apigw, func], [conn])
        return self.processor.process(conn, project)

    def test_generates_three_files(self):
        """APIGW→Lambda produces exactly 3 files: integration, route, permission."""
        files = self._process_apigw_lambda()
        assert len(files) == 3

    def test_integration_file_path(self):
        """Integration file is placed at the correct path."""
        files = self._process_apigw_lambda()
        paths = [f.path for f in files]
        assert (
            "test-project/modules/networking/api-gateway/my-api/integration_my-func.tf"
            in paths
        )

    def test_route_file_path(self):
        """Route file is placed at the correct path."""
        files = self._process_apigw_lambda()
        paths = [f.path for f in files]
        assert (
            "test-project/modules/networking/api-gateway/my-api/route_my-func.tf"
            in paths
        )

    def test_permission_file_path(self):
        """Permission file is placed at the correct path."""
        files = self._process_apigw_lambda()
        paths = [f.path for f in files]
        assert (
            "test-project/modules/networking/api-gateway/my-api/permission_my-func.tf"
            in paths
        )

    def test_route_file_contains_route_resource(self):
        """Route file contains aws_apigatewayv2_route resource."""
        files = self._process_apigw_lambda()
        route_file = next(f for f in files if "route_" in f.path)
        assert "aws_apigatewayv2_route" in route_file.content

    def test_permission_file_contains_permission_resource(self):
        """Permission file contains aws_lambda_permission resource."""
        files = self._process_apigw_lambda()
        perm_file = next(f for f in files if "permission_" in f.path)
        assert "aws_lambda_permission" in perm_file.content

    def test_permission_has_apigateway_principal(self):
        """Permission resource has principal = apigateway.amazonaws.com."""
        files = self._process_apigw_lambda()
        perm_file = next(f for f in files if "permission_" in f.path)
        assert "apigateway.amazonaws.com" in perm_file.content

    def test_uses_defaults_when_no_config(self):
        """Without connection_config, route_key defaults to 'ANY /$default'."""
        files = self._process_apigw_lambda()
        route_file = next(f for f in files if "route_" in f.path)
        assert "ANY /$default" in route_file.content

    def test_uses_connection_config_for_route_key(self):
        """With connection_config, route_key uses provided route_path and http_method."""
        files = self._process_apigw_lambda(
            connection_config={"route_path": "/users", "http_method": "GET"}
        )
        route_file = next(f for f in files if "route_" in f.path)
        assert "GET /users" in route_file.content

    def test_integration_file_contains_integration_resource(self):
        """Integration file contains aws_apigatewayv2_integration resource."""
        files = self._process_apigw_lambda()
        integration_file = next(f for f in files if "integration_" in f.path)
        assert "aws_apigatewayv2_integration" in integration_file.content

    def test_permission_has_source_arn_with_execution_arn(self):
        """Permission resource references the API Gateway execution ARN."""
        files = self._process_apigw_lambda()
        perm_file = next(f for f in files if "permission_" in f.path)
        assert "execution_arn" in perm_file.content

    def test_permission_has_invoke_function_action(self):
        """Permission resource has action = lambda:InvokeFunction."""
        files = self._process_apigw_lambda()
        perm_file = next(f for f in files if "permission_" in f.path)
        assert "lambda:InvokeFunction" in perm_file.content


# ===========================================================================
# 1b. _handle_apigw_lambda_authorizer (connection_role = "authorizer")
# ===========================================================================


class TestHandleApigwLambdaAuthorizer:
    """Test API Gateway → Lambda authorizer handler generates authorizer + permission only."""

    def setup_method(self):
        self.processor = ConnectionProcessor()

    def _process_apigw_lambda_authorizer(self, connection_config=None):
        """Helper: create APIGW→Lambda connection with authorizer role and process it."""
        config = connection_config or {"connection_role": "authorizer"}
        apigw = _apigw_ir("my-api")
        func = _lambda_ir("my-func")
        conn = ConnectionIR(
            source_name="my-api",
            target_name="my-func",
            source_service=ServiceType.API_GATEWAY,
            target_service=ServiceType.LAMBDA,
            connection_type="triggers",
            connection_config=config,
        )
        project = _make_project([apigw, func], [conn])
        return self.processor.process(conn, project)

    def test_generates_two_files(self):
        """Authorizer role produces exactly 2 files: authorizer + permission."""
        files = self._process_apigw_lambda_authorizer()
        assert len(files) == 2

    def test_authorizer_file_path(self):
        """Authorizer file is placed at the correct path."""
        files = self._process_apigw_lambda_authorizer()
        paths = [f.path for f in files]
        assert (
            "test-project/modules/networking/api-gateway/my-api/authorizer_my-func.tf"
            in paths
        )

    def test_permission_file_path(self):
        """Authorizer permission file is placed at the correct path."""
        files = self._process_apigw_lambda_authorizer()
        paths = [f.path for f in files]
        assert (
            "test-project/modules/networking/api-gateway/my-api/authorizer_permission_my-func.tf"
            in paths
        )

    def test_authorizer_contains_authorizer_resource(self):
        """Authorizer file contains aws_apigatewayv2_authorizer resource."""
        files = self._process_apigw_lambda_authorizer()
        auth_file = next(
            f
            for f in files
            if "authorizer_my-func" in f.path and "permission" not in f.path
        )
        assert "aws_apigatewayv2_authorizer" in auth_file.content

    def test_authorizer_has_request_type(self):
        """Authorizer resource has authorizer_type = REQUEST."""
        files = self._process_apigw_lambda_authorizer()
        auth_file = next(
            f
            for f in files
            if "authorizer_my-func" in f.path and "permission" not in f.path
        )
        assert "REQUEST" in auth_file.content

    def test_authorizer_references_lambda_invoke_arn(self):
        """Authorizer resource references the Lambda invoke_arn."""
        files = self._process_apigw_lambda_authorizer()
        auth_file = next(
            f
            for f in files
            if "authorizer_my-func" in f.path and "permission" not in f.path
        )
        assert "aws_lambda_function.my-func.invoke_arn" in auth_file.content

    def test_authorizer_default_payload_format_version(self):
        """Authorizer defaults payload_format_version to 2.0."""
        files = self._process_apigw_lambda_authorizer()
        auth_file = next(
            f
            for f in files
            if "authorizer_my-func" in f.path and "permission" not in f.path
        )
        assert "2.0" in auth_file.content

    def test_authorizer_custom_payload_format_version(self):
        """Authorizer uses custom payload_format_version from config."""
        files = self._process_apigw_lambda_authorizer(
            connection_config={
                "connection_role": "authorizer",
                "payload_format_version": "1.0",
            }
        )
        auth_file = next(
            f
            for f in files
            if "authorizer_my-func" in f.path and "permission" not in f.path
        )
        assert "1.0" in auth_file.content

    def test_authorizer_uses_target_name_as_default_name(self):
        """Authorizer uses target Lambda name as default authorizer name."""
        files = self._process_apigw_lambda_authorizer()
        auth_file = next(
            f
            for f in files
            if "authorizer_my-func" in f.path and "permission" not in f.path
        )
        assert "my-func" in auth_file.content

    def test_authorizer_uses_custom_name(self):
        """Authorizer uses authorizer_name from config when provided."""
        files = self._process_apigw_lambda_authorizer(
            connection_config={
                "connection_role": "authorizer",
                "authorizer_name": "custom-auth",
            }
        )
        auth_file = next(
            f
            for f in files
            if "authorizer_my-func" in f.path and "permission" not in f.path
        )
        assert "custom-auth" in auth_file.content

    def test_permission_contains_lambda_permission_resource(self):
        """Permission file contains aws_lambda_permission resource."""
        files = self._process_apigw_lambda_authorizer()
        perm_file = next(f for f in files if "permission" in f.path)
        assert "aws_lambda_permission" in perm_file.content

    def test_permission_has_apigateway_principal(self):
        """Permission resource has principal = apigateway.amazonaws.com."""
        files = self._process_apigw_lambda_authorizer()
        perm_file = next(f for f in files if "permission" in f.path)
        assert "apigateway.amazonaws.com" in perm_file.content

    def test_permission_has_invoke_function_action(self):
        """Permission resource has action = lambda:InvokeFunction."""
        files = self._process_apigw_lambda_authorizer()
        perm_file = next(f for f in files if "permission" in f.path)
        assert "lambda:InvokeFunction" in perm_file.content

    def test_no_integration_resource_generated(self):
        """Authorizer role does NOT generate integration resources."""
        files = self._process_apigw_lambda_authorizer()
        for f in files:
            assert "aws_apigatewayv2_integration" not in f.content

    def test_no_route_resource_generated(self):
        """Authorizer role does NOT generate route resources."""
        files = self._process_apigw_lambda_authorizer()
        for f in files:
            assert "aws_apigatewayv2_route" not in f.content

    def test_route_handler_still_generates_three_files(self):
        """Explicit route_handler role still produces 3 files (backward compat)."""
        apigw = _apigw_ir("my-api")
        func = _lambda_ir("my-func")
        conn = ConnectionIR(
            source_name="my-api",
            target_name="my-func",
            source_service=ServiceType.API_GATEWAY,
            target_service=ServiceType.LAMBDA,
            connection_type="triggers",
            connection_config={"connection_role": "route_handler"},
        )
        project = _make_project([apigw, func], [conn])
        files = self.processor.process(conn, project)
        assert len(files) == 3


# ===========================================================================
# 2. _handle_lambda_sns
# ===========================================================================


class TestHandleLambdaSns:
    """Test Lambda → SNS handler attaches correct IAM statement."""

    def setup_method(self):
        self.processor = ConnectionProcessor()

    def _process_lambda_sns(self):
        func = _lambda_ir("my-func")
        topic = _sns_ir("my-topic")
        conn = ConnectionIR(
            source_name="my-func",
            target_name="my-topic",
            source_service=ServiceType.LAMBDA,
            target_service=ServiceType.SNS,
            connection_type="publishes_to",
        )
        project = _make_project([func, topic], [conn])
        files = self.processor.process(conn, project)
        return files, func

    def test_returns_no_files(self):
        """Lambda→SNS produces no generated files (IAM only)."""
        files, _ = self._process_lambda_sns()
        assert files == []

    def test_attaches_iam_statement(self):
        """Lambda→SNS attaches exactly one IAM statement to the Lambda."""
        _, func = self._process_lambda_sns()
        assert len(func.iam_statements) == 1

    def test_iam_action_is_sns_publish(self):
        """IAM statement has sns:Publish action."""
        _, func = self._process_lambda_sns()
        stmt = func.iam_statements[0]
        assert "sns:Publish" in stmt.actions

    def test_iam_resource_references_sns_topic_arn(self):
        """IAM resource reference is ${aws_sns_topic.my-topic.arn}."""
        _, func = self._process_lambda_sns()
        stmt = func.iam_statements[0]
        assert "${aws_sns_topic.my-topic.arn}" in stmt.resources

    def test_iam_effect_is_allow(self):
        """IAM statement effect is Allow."""
        _, func = self._process_lambda_sns()
        stmt = func.iam_statements[0]
        assert stmt.effect == "Allow"


# ===========================================================================
# 3. _handle_lambda_sqs
# ===========================================================================


class TestHandleLambdaSqs:
    """Test Lambda → SQS handler attaches correct IAM statement."""

    def setup_method(self):
        self.processor = ConnectionProcessor()

    def _process_lambda_sqs(self):
        func = _lambda_ir("my-func")
        queue = _sqs_ir("my-queue")
        conn = ConnectionIR(
            source_name="my-func",
            target_name="my-queue",
            source_service=ServiceType.LAMBDA,
            target_service=ServiceType.SQS,
            connection_type="sends_to",
        )
        project = _make_project([func, queue], [conn])
        files = self.processor.process(conn, project)
        return files, func

    def test_returns_no_files(self):
        """Lambda→SQS produces no generated files (IAM only)."""
        files, _ = self._process_lambda_sqs()
        assert files == []

    def test_attaches_iam_statement(self):
        """Lambda→SQS attaches exactly one IAM statement to the Lambda."""
        _, func = self._process_lambda_sqs()
        assert len(func.iam_statements) == 1

    def test_iam_action_is_sqs_send_message(self):
        """IAM statement has sqs:SendMessage action."""
        _, func = self._process_lambda_sqs()
        stmt = func.iam_statements[0]
        assert "sqs:SendMessage" in stmt.actions

    def test_iam_resource_references_sqs_queue_arn(self):
        """IAM resource reference is ${aws_sqs_queue.my-queue.arn}."""
        _, func = self._process_lambda_sqs()
        stmt = func.iam_statements[0]
        assert "${aws_sqs_queue.my-queue.arn}" in stmt.resources

    def test_iam_effect_is_allow(self):
        """IAM statement effect is Allow."""
        _, func = self._process_lambda_sqs()
        stmt = func.iam_statements[0]
        assert stmt.effect == "Allow"


# ===========================================================================
# 4. _handle_sqs_lambda
# ===========================================================================


class TestHandleSqsLambda:
    """Test SQS → Lambda handler generates event source mapping, permission, and IAM."""

    def setup_method(self):
        self.processor = ConnectionProcessor()

    def _process_sqs_lambda(self, connection_config=None):
        queue = _sqs_ir("my-queue")
        func = _lambda_ir("my-func")
        conn = ConnectionIR(
            source_name="my-queue",
            target_name="my-func",
            source_service=ServiceType.SQS,
            target_service=ServiceType.LAMBDA,
            connection_type="triggers",
            connection_config=connection_config or {},
        )
        project = _make_project([queue, func], [conn])
        files = self.processor.process(conn, project)
        return files, func

    def test_generates_two_files(self):
        """SQS→Lambda produces exactly 2 files: event source mapping and permission."""
        files, _ = self._process_sqs_lambda()
        assert len(files) == 2

    def test_event_source_mapping_file_path(self):
        """Event source mapping file is placed at the correct path."""
        files, _ = self._process_sqs_lambda()
        paths = [f.path for f in files]
        assert (
            "test-project/modules/messaging/sqs/my-queue/event_source_my-func.tf"
            in paths
        )

    def test_permission_file_path(self):
        """Permission file is placed at the correct path."""
        files, _ = self._process_sqs_lambda()
        paths = [f.path for f in files]
        assert (
            "test-project/modules/messaging/sqs/my-queue/permission_my-func.tf" in paths
        )

    def test_event_source_mapping_contains_resource(self):
        """Event source mapping file contains aws_lambda_event_source_mapping resource."""
        files, _ = self._process_sqs_lambda()
        mapping_file = next(f for f in files if "event_source_" in f.path)
        assert "aws_lambda_event_source_mapping" in mapping_file.content

    def test_batch_size_defaults_to_10(self):
        """Without config, batch_size defaults to 10."""
        files, _ = self._process_sqs_lambda()
        mapping_file = next(f for f in files if "event_source_" in f.path)
        assert "batch_size" in mapping_file.content
        assert "10" in mapping_file.content

    def test_batch_size_uses_config_value(self):
        """With config, batch_size uses the provided value."""
        files, _ = self._process_sqs_lambda(connection_config={"batch_size": 25})
        mapping_file = next(f for f in files if "event_source_" in f.path)
        assert "25" in mapping_file.content

    def test_batching_window_included_when_in_config(self):
        """maximum_batching_window_in_seconds is included when provided in config."""
        files, _ = self._process_sqs_lambda(
            connection_config={"maximum_batching_window_in_seconds": 5}
        )
        mapping_file = next(f for f in files if "event_source_" in f.path)
        assert "maximum_batching_window_in_seconds" in mapping_file.content
        assert "5" in mapping_file.content

    def test_batching_window_absent_when_not_in_config(self):
        """maximum_batching_window_in_seconds is absent when not in config."""
        files, _ = self._process_sqs_lambda()
        mapping_file = next(f for f in files if "event_source_" in f.path)
        assert "maximum_batching_window_in_seconds" not in mapping_file.content

    def test_permission_has_sqs_principal(self):
        """Permission resource has principal = sqs.amazonaws.com."""
        files, _ = self._process_sqs_lambda()
        perm_file = next(f for f in files if "permission_" in f.path)
        assert "sqs.amazonaws.com" in perm_file.content

    def test_attaches_sqs_receive_iam_statements(self):
        """SQS→Lambda attaches SQS receive IAM statements to the Lambda."""
        _, func = self._process_sqs_lambda()
        assert len(func.iam_statements) == 1
        stmt = func.iam_statements[0]
        assert "sqs:ReceiveMessage" in stmt.actions
        assert "sqs:DeleteMessage" in stmt.actions
        assert "sqs:GetQueueAttributes" in stmt.actions

    def test_iam_resource_references_sqs_queue(self):
        """IAM resource reference points to the SQS queue ARN."""
        _, func = self._process_sqs_lambda()
        stmt = func.iam_statements[0]
        assert "${aws_sqs_queue.my-queue.arn}" in stmt.resources


# ===========================================================================
# 5. _handle_sns_sqs
# ===========================================================================


class TestHandleSnsSqs:
    """Test SNS → SQS handler generates subscription and queue policy."""

    def setup_method(self):
        self.processor = ConnectionProcessor()

    def _process_sns_sqs(self):
        topic = _sns_ir("my-topic")
        queue = _sqs_ir("my-queue")
        conn = ConnectionIR(
            source_name="my-topic",
            target_name="my-queue",
            source_service=ServiceType.SNS,
            target_service=ServiceType.SQS,
            connection_type="delivers_to",
        )
        project = _make_project([topic, queue], [conn])
        return self.processor.process(conn, project)

    def test_generates_two_files(self):
        """SNS→SQS produces exactly 2 files: subscription and queue policy."""
        files = self._process_sns_sqs()
        assert len(files) == 2

    def test_subscription_file_path(self):
        """Subscription file is placed at the correct path."""
        files = self._process_sns_sqs()
        paths = [f.path for f in files]
        assert (
            "test-project/modules/messaging/sns/my-topic/subscription_my-queue.tf"
            in paths
        )

    def test_queue_policy_file_path(self):
        """Queue policy file is placed at the correct path."""
        files = self._process_sns_sqs()
        paths = [f.path for f in files]
        assert "test-project/modules/messaging/sqs/my-queue/policy_my-topic.tf" in paths

    def test_subscription_contains_resource(self):
        """Subscription file contains aws_sns_topic_subscription resource."""
        files = self._process_sns_sqs()
        sub_file = next(f for f in files if "subscription_" in f.path)
        assert "aws_sns_topic_subscription" in sub_file.content

    def test_subscription_has_sqs_protocol(self):
        """Subscription has protocol = sqs."""
        files = self._process_sns_sqs()
        sub_file = next(f for f in files if "subscription_" in f.path)
        assert '"sqs"' in sub_file.content

    def test_queue_policy_contains_send_message(self):
        """Queue policy contains SQS:SendMessage action."""
        files = self._process_sns_sqs()
        policy_file = next(f for f in files if "policy_" in f.path)
        assert "SQS:SendMessage" in policy_file.content

    def test_subscription_references_topic_arn(self):
        """Subscription references the SNS topic ARN via Terraform reference."""
        files = self._process_sns_sqs()
        sub_file = next(f for f in files if "subscription_" in f.path)
        assert "aws_sns_topic.my-topic.arn" in sub_file.content

    def test_subscription_references_queue_arn(self):
        """Subscription endpoint references the SQS queue ARN via Terraform reference."""
        files = self._process_sns_sqs()
        sub_file = next(f for f in files if "subscription_" in f.path)
        assert "aws_sqs_queue.my-queue.arn" in sub_file.content


# ===========================================================================
# 6. _handle_sns_lambda
# ===========================================================================


class TestHandleSnsLambda:
    """Test SNS → Lambda handler generates subscription and permission."""

    def setup_method(self):
        self.processor = ConnectionProcessor()

    def _process_sns_lambda(self):
        topic = _sns_ir("my-topic")
        func = _lambda_ir("my-func")
        conn = ConnectionIR(
            source_name="my-topic",
            target_name="my-func",
            source_service=ServiceType.SNS,
            target_service=ServiceType.LAMBDA,
            connection_type="triggers",
        )
        project = _make_project([topic, func], [conn])
        return self.processor.process(conn, project)

    def test_generates_two_files(self):
        """SNS→Lambda produces exactly 2 files: subscription and permission."""
        files = self._process_sns_lambda()
        assert len(files) == 2

    def test_subscription_file_path(self):
        """Subscription file is placed at the correct path."""
        files = self._process_sns_lambda()
        paths = [f.path for f in files]
        assert (
            "test-project/modules/messaging/sns/my-topic/subscription_my-func.tf"
            in paths
        )

    def test_permission_file_path(self):
        """Permission file is placed at the correct path."""
        files = self._process_sns_lambda()
        paths = [f.path for f in files]
        assert (
            "test-project/modules/messaging/sns/my-topic/permission_my-func.tf" in paths
        )

    def test_subscription_contains_resource(self):
        """Subscription file contains aws_sns_topic_subscription resource."""
        files = self._process_sns_lambda()
        sub_file = next(f for f in files if "subscription_" in f.path)
        assert "aws_sns_topic_subscription" in sub_file.content

    def test_subscription_has_lambda_protocol(self):
        """Subscription has protocol = lambda."""
        files = self._process_sns_lambda()
        sub_file = next(f for f in files if "subscription_" in f.path)
        assert '"lambda"' in sub_file.content

    def test_permission_has_sns_principal(self):
        """Permission resource has principal = sns.amazonaws.com."""
        files = self._process_sns_lambda()
        perm_file = next(f for f in files if "permission_" in f.path)
        assert "sns.amazonaws.com" in perm_file.content

    def test_permission_references_sns_topic_arn(self):
        """Permission source_arn references the SNS topic ARN."""
        files = self._process_sns_lambda()
        perm_file = next(f for f in files if "permission_" in f.path)
        assert "aws_sns_topic.my-topic.arn" in perm_file.content

    def test_subscription_references_lambda_arn(self):
        """Subscription endpoint references the Lambda function ARN."""
        files = self._process_sns_lambda()
        sub_file = next(f for f in files if "subscription_" in f.path)
        assert "aws_lambda_function.my-func.arn" in sub_file.content

    def test_permission_has_invoke_function_action(self):
        """Permission resource has action = lambda:InvokeFunction."""
        files = self._process_sns_lambda()
        perm_file = next(f for f in files if "permission_" in f.path)
        assert "lambda:InvokeFunction" in perm_file.content


# ===========================================================================
# 7. Terraform resource reference consistency
# ===========================================================================


class TestTerraformReferenceConsistency:
    """Test all generated resources use Terraform resource references, not hardcoded ARNs."""

    def setup_method(self):
        self.processor = ConnectionProcessor()

    def test_apigw_lambda_uses_terraform_references(self):
        """APIGW→Lambda files reference resources via Terraform syntax, not hardcoded ARNs."""
        apigw = _apigw_ir("my-api")
        func = _lambda_ir("my-func")
        conn = ConnectionIR(
            source_name="my-api",
            target_name="my-func",
            source_service=ServiceType.API_GATEWAY,
            target_service=ServiceType.LAMBDA,
            connection_type="triggers",
        )
        project = _make_project([apigw, func], [conn])
        files = self.processor.process(conn, project)
        for f in files:
            # Should reference resources via Terraform syntax
            assert "arn:aws:" not in f.content, (
                f"File {f.path} contains hardcoded ARN instead of Terraform reference"
            )

    def test_sqs_lambda_uses_terraform_references(self):
        """SQS→Lambda files reference resources via Terraform syntax, not hardcoded ARNs."""
        queue = _sqs_ir("my-queue")
        func = _lambda_ir("my-func")
        conn = ConnectionIR(
            source_name="my-queue",
            target_name="my-func",
            source_service=ServiceType.SQS,
            target_service=ServiceType.LAMBDA,
            connection_type="triggers",
        )
        project = _make_project([queue, func], [conn])
        files = self.processor.process(conn, project)
        for f in files:
            assert "arn:aws:" not in f.content, (
                f"File {f.path} contains hardcoded ARN instead of Terraform reference"
            )

    def test_sns_sqs_uses_terraform_references(self):
        """SNS→SQS files reference resources via Terraform syntax, not hardcoded ARNs."""
        topic = _sns_ir("my-topic")
        queue = _sqs_ir("my-queue")
        conn = ConnectionIR(
            source_name="my-topic",
            target_name="my-queue",
            source_service=ServiceType.SNS,
            target_service=ServiceType.SQS,
            connection_type="delivers_to",
        )
        project = _make_project([topic, queue], [conn])
        files = self.processor.process(conn, project)
        for f in files:
            assert "arn:aws:" not in f.content, (
                f"File {f.path} contains hardcoded ARN instead of Terraform reference"
            )

    def test_sns_lambda_uses_terraform_references(self):
        """SNS→Lambda files reference resources via Terraform syntax, not hardcoded ARNs."""
        topic = _sns_ir("my-topic")
        func = _lambda_ir("my-func")
        conn = ConnectionIR(
            source_name="my-topic",
            target_name="my-func",
            source_service=ServiceType.SNS,
            target_service=ServiceType.LAMBDA,
            connection_type="triggers",
        )
        project = _make_project([topic, func], [conn])
        files = self.processor.process(conn, project)
        for f in files:
            assert "arn:aws:" not in f.content, (
                f"File {f.path} contains hardcoded ARN instead of Terraform reference"
            )

    def test_lambda_sns_iam_uses_terraform_references(self):
        """Lambda→SNS IAM statement uses Terraform resource reference for SNS topic ARN."""
        func = _lambda_ir("my-func")
        topic = _sns_ir("my-topic")
        conn = ConnectionIR(
            source_name="my-func",
            target_name="my-topic",
            source_service=ServiceType.LAMBDA,
            target_service=ServiceType.SNS,
            connection_type="publishes_to",
        )
        project = _make_project([func, topic], [conn])
        self.processor.process(conn, project)
        stmt = func.iam_statements[0]
        for resource in stmt.resources:
            assert resource.startswith("${aws_sns_topic."), (
                f"IAM resource '{resource}' is not a Terraform reference"
            )

    def test_lambda_sqs_iam_uses_terraform_references(self):
        """Lambda→SQS IAM statement uses Terraform resource reference for SQS queue ARN."""
        func = _lambda_ir("my-func")
        queue = _sqs_ir("my-queue")
        conn = ConnectionIR(
            source_name="my-func",
            target_name="my-queue",
            source_service=ServiceType.LAMBDA,
            target_service=ServiceType.SQS,
            connection_type="sends_to",
        )
        project = _make_project([func, queue], [conn])
        self.processor.process(conn, project)
        stmt = func.iam_statements[0]
        for resource in stmt.resources:
            assert resource.startswith("${aws_sqs_queue."), (
                f"IAM resource '{resource}' is not a Terraform reference"
            )

    def test_sqs_lambda_iam_uses_terraform_references(self):
        """SQS→Lambda IAM statements use Terraform resource reference for SQS queue ARN."""
        queue = _sqs_ir("my-queue")
        func = _lambda_ir("my-func")
        conn = ConnectionIR(
            source_name="my-queue",
            target_name="my-func",
            source_service=ServiceType.SQS,
            target_service=ServiceType.LAMBDA,
            connection_type="triggers",
        )
        project = _make_project([queue, func], [conn])
        self.processor.process(conn, project)
        stmt = func.iam_statements[0]
        for resource in stmt.resources:
            assert resource.startswith("${aws_sqs_queue."), (
                f"IAM resource '{resource}' is not a Terraform reference"
            )


# ===========================================================================
# 8. Lambda → DynamoDB access_pattern handling
# ===========================================================================


def _dynamodb_ir(name: str = "my-table") -> ResourceInstanceIR:
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.DYNAMODB,
        config=DynamoDBConfig(table_name="test-table", hash_key_type="S", hash_key="id", billing_mode="PAY_PER_REQUEST"),
    )


class TestHandleLambdaDynamoDBAccessPattern:
    """Test Lambda → DynamoDB handler respects access_pattern config."""

    def setup_method(self):
        self.processor = ConnectionProcessor()

    def _process_lambda_dynamodb(self, connection_config=None):
        func = _lambda_ir("my-func")
        table = _dynamodb_ir("my-table")
        conn = ConnectionIR(
            source_name="my-func",
            target_name="my-table",
            source_service=ServiceType.LAMBDA,
            target_service=ServiceType.DYNAMODB,
            connection_type="reads_from",
            connection_config=connection_config or {},
        )
        project = _make_project([func, table], [conn])
        self.processor.process(conn, project)
        return func

    def test_default_access_pattern_uses_all_actions(self):
        """No access_pattern specified → all 6 DynamoDB actions (full access)."""
        func = self._process_lambda_dynamodb()
        assert len(func.iam_statements) == 1
        actions = func.iam_statements[0].actions
        assert "dynamodb:GetItem" in actions
        assert "dynamodb:Query" in actions
        assert "dynamodb:Scan" in actions
        assert "dynamodb:PutItem" in actions
        assert "dynamodb:UpdateItem" in actions
        assert "dynamodb:DeleteItem" in actions

    def test_full_access_pattern_uses_all_actions(self):
        """access_pattern="full" → all 6 DynamoDB actions."""
        func = self._process_lambda_dynamodb({"access_pattern": "full"})
        assert len(func.iam_statements) == 1
        actions = func.iam_statements[0].actions
        assert "dynamodb:GetItem" in actions
        assert "dynamodb:Query" in actions
        assert "dynamodb:Scan" in actions
        assert "dynamodb:PutItem" in actions
        assert "dynamodb:UpdateItem" in actions
        assert "dynamodb:DeleteItem" in actions

    def test_read_access_pattern_uses_only_read_actions(self):
        """access_pattern="read" → only GetItem, Query, Scan."""
        func = self._process_lambda_dynamodb({"access_pattern": "read"})
        assert len(func.iam_statements) == 1
        actions = func.iam_statements[0].actions
        assert actions == ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]

    def test_write_access_pattern_uses_only_write_actions(self):
        """access_pattern="write" → only PutItem, UpdateItem, DeleteItem."""
        func = self._process_lambda_dynamodb({"access_pattern": "write"})
        assert len(func.iam_statements) == 1
        actions = func.iam_statements[0].actions
        assert actions == [
            "dynamodb:PutItem",
            "dynamodb:UpdateItem",
            "dynamodb:DeleteItem",
        ]

    def test_read_access_pattern_excludes_write_actions(self):
        """access_pattern="read" must NOT include write actions."""
        func = self._process_lambda_dynamodb({"access_pattern": "read"})
        actions = func.iam_statements[0].actions
        assert "dynamodb:PutItem" not in actions
        assert "dynamodb:UpdateItem" not in actions
        assert "dynamodb:DeleteItem" not in actions

    def test_write_access_pattern_excludes_read_actions(self):
        """access_pattern="write" must NOT include read actions."""
        func = self._process_lambda_dynamodb({"access_pattern": "write"})
        actions = func.iam_statements[0].actions
        assert "dynamodb:GetItem" not in actions
        assert "dynamodb:Query" not in actions
        assert "dynamodb:Scan" not in actions

    def test_iam_resource_references_dynamodb_table(self):
        """IAM statement resource references the DynamoDB table ARN via Terraform."""
        func = self._process_lambda_dynamodb({"access_pattern": "read"})
        stmt = func.iam_statements[0]
        assert "${aws_dynamodb_table.my-table.arn}" in stmt.resources


# ===========================================================================
# 9. Lambda → S3 access_pattern
# ===========================================================================


def _s3_ir(name: str = "my-bucket") -> ResourceInstanceIR:
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.S3,
        config=S3Config(),
    )


class TestHandleLambdaS3AccessPattern:
    """Test Lambda → S3 handler respects access_pattern config."""

    def setup_method(self):
        self.processor = ConnectionProcessor()

    def _process_lambda_s3(self, connection_config=None):
        func = _lambda_ir("my-func")
        bucket = _s3_ir("my-bucket")
        conn = ConnectionIR(
            source_name="my-func",
            target_name="my-bucket",
            source_service=ServiceType.LAMBDA,
            target_service=ServiceType.S3,
            connection_type="writes_to",
            connection_config=connection_config or {},
        )
        project = _make_project([func, bucket], [conn])
        self.processor.process(conn, project)
        return func

    def test_default_access_pattern_uses_all_actions(self):
        """No access_pattern specified → all 4 S3 actions (full access)."""
        func = self._process_lambda_s3()
        assert len(func.iam_statements) == 1
        actions = func.iam_statements[0].actions
        assert "s3:GetObject" in actions
        assert "s3:PutObject" in actions
        assert "s3:DeleteObject" in actions
        assert "s3:ListBucket" in actions

    def test_full_access_pattern_uses_all_actions(self):
        """access_pattern="full" → all 4 S3 actions."""
        func = self._process_lambda_s3({"access_pattern": "full"})
        assert len(func.iam_statements) == 1
        actions = func.iam_statements[0].actions
        assert "s3:GetObject" in actions
        assert "s3:PutObject" in actions
        assert "s3:DeleteObject" in actions
        assert "s3:ListBucket" in actions

    def test_read_access_pattern_uses_only_read_actions(self):
        """access_pattern="read" → only GetObject, ListBucket."""
        func = self._process_lambda_s3({"access_pattern": "read"})
        assert len(func.iam_statements) == 1
        actions = func.iam_statements[0].actions
        assert actions == ["s3:GetObject", "s3:ListBucket"]

    def test_write_access_pattern_uses_only_write_actions(self):
        """access_pattern="write" → only PutObject, DeleteObject."""
        func = self._process_lambda_s3({"access_pattern": "write"})
        assert len(func.iam_statements) == 1
        actions = func.iam_statements[0].actions
        assert actions == ["s3:PutObject", "s3:DeleteObject"]

    def test_read_access_pattern_excludes_write_actions(self):
        """access_pattern="read" must NOT include write actions."""
        func = self._process_lambda_s3({"access_pattern": "read"})
        actions = func.iam_statements[0].actions
        assert "s3:PutObject" not in actions
        assert "s3:DeleteObject" not in actions

    def test_write_access_pattern_excludes_read_actions(self):
        """access_pattern="write" must NOT include read actions."""
        func = self._process_lambda_s3({"access_pattern": "write"})
        actions = func.iam_statements[0].actions
        assert "s3:GetObject" not in actions
        assert "s3:ListBucket" not in actions

    def test_iam_resources_include_bucket_and_objects(self):
        """IAM statement resources include both bucket ARN and bucket/* ARN."""
        func = self._process_lambda_s3({"access_pattern": "read"})
        stmt = func.iam_statements[0]
        assert "${aws_s3_bucket.my-bucket.arn}" in stmt.resources
        assert "${aws_s3_bucket.my-bucket.arn}/*" in stmt.resources
