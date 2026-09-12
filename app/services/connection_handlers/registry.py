"""Connection registry — the single source of truth for which connections exist."""

from dataclasses import dataclass
from typing import Literal

from app.models.connection_configs._base import BaseConnectionConfig
from app.models.connection_configs.backup import BackupSelectionConfig
from app.models.connection_configs.configs import (
    AcceleratorEndpointConfig,
    ApiGatewayAuthorizerConfig,
    ApiGatewayRouteHandlerConfig,
    DnsAliasConfig,
    DynamoDBLambdaConfig,
    EcsTargetGroupConfig,
    EmptyConnectionConfig,
    EventBridgeTargetConfig,
    GatewayRouteConfig,
    LambdaDynamoDBConfig,
    LambdaS3Config,
    LoadBalancerListenerConfig,
    S3LambdaConfig,
    SqsLambdaConfig,
    TargetGroupAttachmentConfig,
)
from app.models.connection_configs.replication import S3ReplicationConfig
from app.models.connection_configs.secrets import (
    AppRunnerSecretConfig,
    BatchSecretConfig,
    CodeBuildSecretConfig,
    EcsSecretConfig,
)
from app.models.connection_configs.storage import (
    EbsAttachmentConfig,
    EfsLambdaMountConfig,
    S3LocationConfig,
    S3NotificationConfig,
)
from app.models.connection_configs.workflows import StepFunctionsSecretConfig
from app.models.input_models import ServiceType
from app.services.connection_handlers.accelerator_endpoint import (
    AcceleratorLoadBalancerHandler,
)
from app.services.connection_handlers.apigw_lambda import ApiGatewayLambdaHandler
from app.services.connection_handlers.backup_selection import (
    BACKUP_OUTPUTS,
    BackupSelectionHandler,
)
from app.services.connection_handlers.base import ConnectionHandler
from app.services.connection_handlers.certificate import (
    CertificateCloudFrontHandler,
    CertificateLoadBalancerHandler,
)
from app.services.connection_handlers.cloudfront_s3 import CloudFrontS3Handler
from app.services.connection_handlers.datasync_location import DataSyncLocationHandler
from app.services.connection_handlers.datasync_s3 import DataSyncS3Handler
from app.services.connection_handlers.dns_alias import DnsAliasHandler
from app.services.connection_handlers.dynamodb_lambda import DynamoDBLambdaHandler
from app.services.connection_handlers.ebs_attachment import EbsAttachmentHandler
from app.services.connection_handlers.ec2_placement import (
    SecurityGroupEC2AssociationHandler,
    SubnetEC2PlacementHandler,
)
from app.services.connection_handlers.ec2_secret import Ec2SecretHandler
from app.services.connection_handlers.ecs_secret import EcsSecretHandler
from app.services.connection_handlers.ecs_target_group import TargetGroupECSHandler
from app.services.connection_handlers.efs_lambda import EfsLambdaMountHandler
from app.services.connection_handlers.environment_secret import EnvironmentSecretHandler
from app.services.connection_handlers.eventbridge_targets import (
    EventBridgeLambdaHandler,
    EventBridgeSQSHandler,
)
from app.services.connection_handlers.firehose_s3 import FirehoseS3Handler
from app.services.connection_handlers.gateway_route import GatewayRouteHandler
from app.services.connection_handlers.iam_grant import IamGrantHandler
from app.services.connection_handlers.kms_cloudtrail import KmsCloudTrailHandler
from app.services.connection_handlers.kms_encryption import KmsEncryptionHandler
from app.services.connection_handlers.kms_references import KMS_INPUTS
from app.services.connection_handlers.lambda_cloudwatch import LambdaCloudWatchHandler
from app.services.connection_handlers.launch_template import (
    LaunchTemplateAutoScalingHandler,
)
from app.services.connection_handlers.load_balancer_listener import (
    LoadBalancerTargetGroupHandler,
)
from app.services.connection_handlers.mwaa_secret import MwaaSecretHandler
from app.services.connection_handlers.network_placement import (
    ListPlacementHandler,
    SecurityGroupListAssociationHandler,
    SubnetListPlacementHandler,
)
from app.services.connection_handlers.route53_vpc_association import (
    Route53VpcAssociationHandler,
)
from app.services.connection_handlers.route_table_association import (
    RouteTableAssociationHandler,
)
from app.services.connection_handlers.s3_destination import S3DestinationHandler
from app.services.connection_handlers.s3_eventbridge import S3EventBridgeHandler
from app.services.connection_handlers.s3_lambda import S3LambdaHandler
from app.services.connection_handlers.s3_location import (
    LakeFormationS3Handler,
    S3LocationHandler,
)
from app.services.connection_handlers.s3_log_delivery import S3LogDeliveryHandler
from app.services.connection_handlers.s3_read_source import S3ReadSourceHandler
from app.services.connection_handlers.s3_replication import S3ReplicationHandler
from app.services.connection_handlers.secret_access import SecretAccessHandler
from app.services.connection_handlers.sns_lambda import SNSLambdaHandler
from app.services.connection_handlers.sns_sqs import SNSSQSHandler
from app.services.connection_handlers.sqs_lambda import SQSLambdaHandler
from app.services.connection_handlers.step_functions_secret import (
    StepFunctionsSecretHandler,
)
from app.services.connection_handlers.subnet_membership import SubnetMembershipHandler
from app.services.connection_handlers.target_group_attachment import (
    TargetGroupEC2AttachmentHandler,
)
from app.services.connection_handlers.target_group_lambda import (
    TargetGroupLambdaAttachmentHandler,
)
from app.services.connection_handlers.vpc_membership import VpcMembershipHandler
from app.services.connection_handlers.waf_association import (
    WafCloudFrontHandler,
    WafLoadBalancerHandler,
)


@dataclass(frozen=True)
class ConnectionSpec:
    """Everything the system knows about one kind of connection."""

    source: ServiceType
    target: ServiceType
    connection_type: str
    label: str
    config_model: type[BaseConnectionConfig]
    handler: ConnectionHandler
    # Chosen when a payload does not name a connection_type for this pair
    is_default: bool = True
    region_policy: Literal["same-region", "cross-region"] = "same-region"

    @property
    def key(self) -> tuple[ServiceType, ServiceType, str]:
        return (self.source, self.target, self.connection_type)


CONNECTION_SPECS: list[ConnectionSpec] = [
    ConnectionSpec(
        source=ServiceType.DATASYNC_S3_LOCATION,
        target=ServiceType.S3,
        connection_type="uses_bucket",
        label="DataSync location → S3",
        config_model=EmptyConnectionConfig,
        handler=DataSyncS3Handler(),
    ),
    *[
        ConnectionSpec(
            source=ServiceType.DATASYNC,
            target=ServiceType.DATASYNC_S3_LOCATION,
            connection_type=kind,
            label=f"DataSync → {label} location",
            config_model=EmptyConnectionConfig,
            handler=DataSyncLocationHandler(field),
            is_default=kind == "reads_from",
        )
        for kind, label, field in [
            ("reads_from", "source", "source_location_arn"),
            ("writes_to", "destination", "destination_location_arn"),
        ]
    ],
    ConnectionSpec(
        source=ServiceType.CLOUDFRONT,
        target=ServiceType.S3,
        connection_type="origin",
        label="CloudFront → private S3 origin",
        config_model=EmptyConnectionConfig,
        handler=CloudFrontS3Handler(),
        region_policy="cross-region",
    ),
    ConnectionSpec(
        source=ServiceType.KINESIS_FIREHOSE,
        target=ServiceType.S3,
        connection_type="delivers_to",
        label="Firehose → S3 destination",
        config_model=S3LocationConfig,
        handler=FirehoseS3Handler(),
    ),
    ConnectionSpec(
        source=ServiceType.MWAA,
        target=ServiceType.S3,
        connection_type="reads_source",
        label="MWAA → S3 source",
        config_model=EmptyConnectionConfig,
        handler=S3ReadSourceHandler("execution_role_arn", "source_bucket_arn", True),
    ),
    ConnectionSpec(
        source=ServiceType.COMPREHEND,
        target=ServiceType.S3,
        connection_type="trains_from",
        label="Comprehend → S3 training data",
        config_model=S3LocationConfig,
        handler=S3ReadSourceHandler("data_access_role_arn", "training_data_s3_uri"),
    ),
    *[
        ConnectionSpec(
            source=source,
            target=ServiceType.S3,
            connection_type="delivers_to",
            label=f"{source.value} → S3 delivery",
            config_model=EmptyConnectionConfig,
            handler=S3LogDeliveryHandler(),
            region_policy="cross-region",
        )
        for source in (ServiceType.CLOUDTRAIL, ServiceType.AWS_CONFIG)
    ],
    ConnectionSpec(
        source=ServiceType.S3,
        target=ServiceType.S3,
        connection_type="replicates_to",
        label="S3 → S3 replication",
        config_model=S3ReplicationConfig,
        handler=S3ReplicationHandler(),
        region_policy="cross-region",
    ),
    ConnectionSpec(
        source=ServiceType.ATHENA,
        target=ServiceType.S3,
        connection_type="stores_results",
        label="Athena → S3 results",
        config_model=S3LocationConfig,
        handler=S3LocationHandler(
            "output_location",
            True,
            "Query callers must have S3 and any KMS permissions for the result location. This workgroup connection does not create a query execution identity or data catalog.",
        ),
    ),
    ConnectionSpec(
        source=ServiceType.LAKE_FORMATION,
        target=ServiceType.S3,
        connection_type="registers",
        label="Lake Formation → S3 registration",
        config_model=S3LocationConfig,
        handler=LakeFormationS3Handler(),
    ),
    *[
        ConnectionSpec(
            source=ServiceType.BACKUP,
            target=target,
            connection_type="backs_up",
            label=f"Backup → {target.value}",
            config_model=BackupSelectionConfig,
            handler=BackupSelectionHandler(),
        )
        for target in BACKUP_OUTPUTS
    ],
    ConnectionSpec(
        source=ServiceType.EFS,
        target=ServiceType.LAMBDA,
        connection_type="mounts",
        label="EFS → Lambda",
        config_model=EfsLambdaMountConfig,
        handler=EfsLambdaMountHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.EBS,
        target=ServiceType.EC2,
        connection_type="attaches",
        label="EBS → EC2",
        config_model=EbsAttachmentConfig,
        handler=EbsAttachmentHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.S3,
        target=ServiceType.EVENTBRIDGE,
        connection_type="delivers_to",
        label="S3 → EventBridge",
        config_model=EmptyConnectionConfig,
        handler=S3EventBridgeHandler(),
    ),
    *[
        ConnectionSpec(
            source=ServiceType.S3,
            target=target,
            connection_type="notifies",
            label=f"S3 → {target.value.upper()}",
            config_model=S3NotificationConfig,
            handler=S3DestinationHandler(),
        )
        for target in (ServiceType.SNS, ServiceType.SQS)
    ],
    ConnectionSpec(
        source=ServiceType.BATCH_JOB_DEFINITION,
        target=ServiceType.SECRETS_MANAGER,
        connection_type="injects_secret",
        label="Batch Job Definition → Secrets Manager (environment injection)",
        config_model=BatchSecretConfig,
        handler=EnvironmentSecretHandler(
            BatchSecretConfig, "execution_role_arn", "Batch job definition"
        ),
    ),
    ConnectionSpec(
        source=ServiceType.STEP_FUNCTIONS,
        target=ServiceType.SECRETS_MANAGER,
        connection_type="reads_secret",
        label="Step Functions → Secrets Manager (GetSecretValue task)",
        config_model=StepFunctionsSecretConfig,
        handler=StepFunctionsSecretHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.MWAA,
        target=ServiceType.SECRETS_MANAGER,
        connection_type="reads_secret",
        label="MWAA → Secrets Manager (DAG read access)",
        config_model=EmptyConnectionConfig,
        handler=MwaaSecretHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.EC2_LAUNCH_TEMPLATE,
        target=ServiceType.EC2_AUTO_SCALING,
        connection_type="launches",
        label="EC2 Launch Template → EC2 Auto Scaling",
        config_model=EmptyConnectionConfig,
        handler=LaunchTemplateAutoScalingHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.APP_RUNNER,
        target=ServiceType.SECRETS_MANAGER,
        connection_type="injects_secret",
        label="App Runner → Secrets Manager (environment injection)",
        config_model=AppRunnerSecretConfig,
        handler=EnvironmentSecretHandler(
            AppRunnerSecretConfig, "instance_role_arn", "App Runner"
        ),
    ),
    ConnectionSpec(
        source=ServiceType.CODEBUILD,
        target=ServiceType.SECRETS_MANAGER,
        connection_type="injects_secret",
        label="CodeBuild → Secrets Manager (environment injection)",
        config_model=CodeBuildSecretConfig,
        handler=EnvironmentSecretHandler(
            CodeBuildSecretConfig, "service_role", "CodeBuild"
        ),
    ),
    ConnectionSpec(
        source=ServiceType.EC2,
        target=ServiceType.SECRETS_MANAGER,
        connection_type="reads_secret",
        label="EC2 → Secrets Manager (read access)",
        config_model=EmptyConnectionConfig,
        handler=Ec2SecretHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.LAMBDA,
        target=ServiceType.SECRETS_MANAGER,
        connection_type="reads_secret",
        label="Lambda → Secrets Manager (read access)",
        config_model=EmptyConnectionConfig,
        handler=SecretAccessHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.ECS,
        target=ServiceType.SECRETS_MANAGER,
        connection_type="injects_secret",
        label="ECS → Secrets Manager (environment injection)",
        config_model=EcsSecretConfig,
        handler=EcsSecretHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.VPC,
        target=ServiceType.SUBNET,
        connection_type="contains",
        label="VPC → Subnet",
        config_model=EmptyConnectionConfig,
        handler=VpcMembershipHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.VPC,
        target=ServiceType.SECURITY_GROUP,
        connection_type="contains",
        label="VPC → Security Group",
        config_model=EmptyConnectionConfig,
        handler=VpcMembershipHandler(),
    ),
    *[
        ConnectionSpec(
            source=ServiceType.VPC,
            target=target,
            connection_type="contains",
            label=f"VPC → {target.value}",
            config_model=EmptyConnectionConfig,
            handler=VpcMembershipHandler(),
        )
        for target in (
            ServiceType.ROUTE_TABLE,
            ServiceType.INTERNET_GATEWAY,
            ServiceType.TARGET_GROUP,
        )
    ],
    ConnectionSpec(
        source=ServiceType.VPC,
        target=ServiceType.NETWORK_FIREWALL,
        connection_type="contains",
        label="VPC → Network Firewall",
        config_model=EmptyConnectionConfig,
        handler=VpcMembershipHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.VPC,
        target=ServiceType.ROUTE53,
        connection_type="contains",
        label="VPC → private Route 53 hosted zone",
        config_model=EmptyConnectionConfig,
        handler=Route53VpcAssociationHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.SUBNET,
        target=ServiceType.NAT_GATEWAY,
        connection_type="contains",
        label="Subnet → NAT Gateway",
        config_model=EmptyConnectionConfig,
        handler=SubnetMembershipHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.SUBNET,
        target=ServiceType.ROUTE_TABLE,
        connection_type="associates",
        label="Subnet → Route Table",
        config_model=EmptyConnectionConfig,
        handler=RouteTableAssociationHandler(),
    ),
    *[
        ConnectionSpec(
            source=source,
            target=ServiceType.ROUTE_TABLE,
            connection_type="routes",
            label=f"{source.value} → Route Table",
            config_model=GatewayRouteConfig,
            handler=GatewayRouteHandler(output_name, argument_name),
        )
        for source, output_name, argument_name in (
            (
                ServiceType.INTERNET_GATEWAY,
                "internet_gateway_id",
                "gateway_id",
            ),
            (ServiceType.NAT_GATEWAY, "nat_gateway_id", "nat_gateway_id"),
            (
                ServiceType.TRANSIT_GATEWAY,
                "transit_gateway_id",
                "transit_gateway_id",
            ),
        )
    ],
    ConnectionSpec(
        source=ServiceType.SUBNET,
        target=ServiceType.EC2,
        connection_type="places",
        label="Subnet → EC2",
        config_model=EmptyConnectionConfig,
        handler=SubnetEC2PlacementHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.SECURITY_GROUP,
        target=ServiceType.EC2,
        connection_type="associates",
        label="Security Group → EC2",
        config_model=EmptyConnectionConfig,
        handler=SecurityGroupEC2AssociationHandler(),
    ),
    *[
        ConnectionSpec(
            source=ServiceType.SUBNET,
            target=target,
            connection_type="places",
            label=f"Subnet → {target.value}",
            config_model=EmptyConnectionConfig,
            handler=SubnetListPlacementHandler(
                "vpc_subnet_ids" if target is ServiceType.LAMBDA else "subnet_ids"
            ),
        )
        for target in (
            ServiceType.LAMBDA,
            ServiceType.EKS,
            ServiceType.EC2_AUTO_SCALING,
            ServiceType.LOAD_BALANCER,
            ServiceType.EFS,
            ServiceType.MEMORYDB,
            ServiceType.DATABASE_MIGRATION_SERVICE,
            ServiceType.MQ,
            ServiceType.MWAA,
            ServiceType.NETWORK_FIREWALL,
            ServiceType.CLIENT_VPN,
        )
    ],
    *[
        ConnectionSpec(
            source=ServiceType.SECURITY_GROUP,
            target=target,
            connection_type="associates",
            label=f"Security Group → {target.value}",
            config_model=EmptyConnectionConfig,
            handler=SecurityGroupListAssociationHandler(
                "vpc_security_group_ids"
                if target
                in {ServiceType.LAMBDA, ServiceType.DATABASE_MIGRATION_SERVICE}
                else "security_group_ids"
            ),
        )
        for target in (
            ServiceType.LAMBDA,
            ServiceType.EKS,
            ServiceType.EC2_LAUNCH_TEMPLATE,
            ServiceType.LOAD_BALANCER,
            ServiceType.EFS,
            ServiceType.MEMORYDB,
            ServiceType.DATABASE_MIGRATION_SERVICE,
            ServiceType.MQ,
            ServiceType.MWAA,
            ServiceType.CLIENT_VPN,
        )
    ],
    ConnectionSpec(
        source=ServiceType.KMS,
        target=ServiceType.CLOUDTRAIL,
        connection_type="encrypts",
        label="KMS → CloudTrail",
        config_model=EmptyConnectionConfig,
        handler=KmsCloudTrailHandler(),
    ),
    *[
        ConnectionSpec(
            source=ServiceType.KMS,
            target=target,
            connection_type="encrypts",
            label=f"KMS → {target.value}",
            config_model=EmptyConnectionConfig,
            handler=KmsEncryptionHandler(input_name),
        )
        for target, input_name in KMS_INPUTS.items()
        if target != ServiceType.CLOUDTRAIL
    ],
    ConnectionSpec(
        source=ServiceType.CERTIFICATE_MANAGER,
        target=ServiceType.LOAD_BALANCER,
        connection_type="secures",
        label="Certificate Manager → Load Balancer",
        config_model=EmptyConnectionConfig,
        handler=CertificateLoadBalancerHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.CERTIFICATE_MANAGER,
        target=ServiceType.CLOUDFRONT,
        connection_type="secures",
        label="Certificate Manager → CloudFront",
        config_model=EmptyConnectionConfig,
        handler=CertificateCloudFrontHandler(),
        region_policy="cross-region",
    ),
    ConnectionSpec(
        source=ServiceType.WAF,
        target=ServiceType.LOAD_BALANCER,
        connection_type="protects",
        label="WAF → Load Balancer",
        config_model=EmptyConnectionConfig,
        handler=WafLoadBalancerHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.WAF,
        target=ServiceType.CLOUDFRONT,
        connection_type="protects",
        label="WAF → CloudFront",
        config_model=EmptyConnectionConfig,
        handler=WafCloudFrontHandler(),
    ),
    *[
        ConnectionSpec(
            source=ServiceType.ROUTE53,
            target=target,
            connection_type="aliases",
            label=f"Route 53 → {target.value}",
            config_model=DnsAliasConfig,
            handler=DnsAliasHandler(dns_output, zone_output),
        )
        for target, dns_output, zone_output in (
            (ServiceType.LOAD_BALANCER, "dns_name", "zone_id"),
            (ServiceType.CLOUDFRONT, "domain_name", "hosted_zone_id"),
            (ServiceType.GLOBAL_ACCELERATOR, "dns_name", "hosted_zone_id"),
        )
    ],
    ConnectionSpec(
        source=ServiceType.GLOBAL_ACCELERATOR,
        target=ServiceType.LOAD_BALANCER,
        connection_type="accelerates",
        label="Global Accelerator → Load Balancer",
        config_model=AcceleratorEndpointConfig,
        handler=AcceleratorLoadBalancerHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.LOAD_BALANCER,
        target=ServiceType.TARGET_GROUP,
        connection_type="forwards_to",
        label="Load Balancer → Target Group",
        config_model=LoadBalancerListenerConfig,
        handler=LoadBalancerTargetGroupHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.TARGET_GROUP,
        target=ServiceType.EC2,
        connection_type="attaches",
        label="Target Group → EC2",
        config_model=TargetGroupAttachmentConfig,
        handler=TargetGroupEC2AttachmentHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.TARGET_GROUP,
        target=ServiceType.ECS,
        connection_type="serves",
        label="Target Group → ECS",
        config_model=EcsTargetGroupConfig,
        handler=TargetGroupECSHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.TARGET_GROUP,
        target=ServiceType.LAMBDA,
        connection_type="attaches",
        label="Target Group → Lambda",
        config_model=EmptyConnectionConfig,
        handler=TargetGroupLambdaAttachmentHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.TARGET_GROUP,
        target=ServiceType.EC2_AUTO_SCALING,
        connection_type="attaches",
        label="Target Group → EC2 Auto Scaling",
        config_model=EmptyConnectionConfig,
        handler=ListPlacementHandler(
            ServiceType.TARGET_GROUP,
            "attaches",
            "target_group_arns",
            "target_group_arn",
            "Target groups attached to this Auto Scaling group",
        ),
    ),
    ConnectionSpec(
        source=ServiceType.API_GATEWAY,
        target=ServiceType.LAMBDA,
        connection_type="route_handler",
        label="API Gateway → Lambda (route handler)",
        config_model=ApiGatewayRouteHandlerConfig,
        handler=ApiGatewayLambdaHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.API_GATEWAY,
        target=ServiceType.LAMBDA,
        connection_type="authorizer",
        label="API Gateway → Lambda (authorizer)",
        config_model=ApiGatewayAuthorizerConfig,
        handler=ApiGatewayLambdaHandler(),
        is_default=False,
    ),
    ConnectionSpec(
        source=ServiceType.LAMBDA,
        target=ServiceType.DYNAMODB,
        connection_type="accesses",
        label="Lambda → DynamoDB",
        config_model=LambdaDynamoDBConfig,
        handler=IamGrantHandler(ServiceType.DYNAMODB),
        region_policy="cross-region",
    ),
    ConnectionSpec(
        source=ServiceType.LAMBDA,
        target=ServiceType.S3,
        connection_type="accesses",
        label="Lambda → S3",
        config_model=LambdaS3Config,
        handler=IamGrantHandler(ServiceType.S3),
        region_policy="cross-region",
    ),
    ConnectionSpec(
        source=ServiceType.LAMBDA,
        target=ServiceType.CLOUDWATCH,
        connection_type="logs_to",
        label="Lambda → CloudWatch",
        config_model=EmptyConnectionConfig,
        handler=LambdaCloudWatchHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.LAMBDA,
        target=ServiceType.SNS,
        connection_type="publishes_to",
        label="Lambda → SNS",
        config_model=EmptyConnectionConfig,
        handler=IamGrantHandler(ServiceType.SNS, access_pattern="full"),
        region_policy="cross-region",
    ),
    ConnectionSpec(
        source=ServiceType.LAMBDA,
        target=ServiceType.SQS,
        connection_type="sends_to",
        label="Lambda → SQS",
        config_model=EmptyConnectionConfig,
        handler=IamGrantHandler(ServiceType.SQS, access_pattern="write"),
        region_policy="cross-region",
    ),
    ConnectionSpec(
        source=ServiceType.S3,
        target=ServiceType.LAMBDA,
        connection_type="notifies",
        label="S3 → Lambda",
        config_model=S3LambdaConfig,
        handler=S3LambdaHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.DYNAMODB,
        target=ServiceType.LAMBDA,
        connection_type="streams_to",
        label="DynamoDB Streams → Lambda",
        config_model=DynamoDBLambdaConfig,
        handler=DynamoDBLambdaHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.ECS,
        target=ServiceType.DYNAMODB,
        connection_type="accesses",
        label="ECS → DynamoDB",
        config_model=LambdaDynamoDBConfig,
        handler=IamGrantHandler(ServiceType.DYNAMODB),
        region_policy="cross-region",
    ),
    ConnectionSpec(
        source=ServiceType.ECS,
        target=ServiceType.S3,
        connection_type="accesses",
        label="ECS → S3",
        config_model=LambdaS3Config,
        handler=IamGrantHandler(ServiceType.S3),
        region_policy="cross-region",
    ),
    ConnectionSpec(
        source=ServiceType.EVENTBRIDGE,
        target=ServiceType.LAMBDA,
        connection_type="targets",
        label="EventBridge → Lambda",
        config_model=EventBridgeTargetConfig,
        handler=EventBridgeLambdaHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.EVENTBRIDGE,
        target=ServiceType.SQS,
        connection_type="targets",
        label="EventBridge → SQS",
        config_model=EventBridgeTargetConfig,
        handler=EventBridgeSQSHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.SQS,
        target=ServiceType.LAMBDA,
        connection_type="triggers",
        label="SQS → Lambda",
        config_model=SqsLambdaConfig,
        handler=SQSLambdaHandler(),
    ),
    ConnectionSpec(
        source=ServiceType.SNS,
        target=ServiceType.SQS,
        connection_type="delivers_to",
        label="SNS → SQS",
        config_model=EmptyConnectionConfig,
        handler=SNSSQSHandler(),
        region_policy="cross-region",
    ),
    ConnectionSpec(
        source=ServiceType.SNS,
        target=ServiceType.LAMBDA,
        connection_type="triggers",
        label="SNS → Lambda",
        config_model=EmptyConnectionConfig,
        handler=SNSLambdaHandler(),
    ),
]

CONNECTION_REGISTRY: dict[tuple[ServiceType, ServiceType, str], ConnectionSpec] = {
    spec.key: spec for spec in CONNECTION_SPECS
}

# Derived so a registered connection is legal by construction
COMPATIBLE_CONNECTIONS: set[tuple[ServiceType, ServiceType]] = {
    (spec.source, spec.target) for spec in CONNECTION_SPECS
}


def resolve_spec(
    source: ServiceType, target: ServiceType, connection_type: str, config: dict
) -> ConnectionSpec | None:
    """Find the spec for a connection, tolerating payloads that do not name a type."""
    exact = CONNECTION_REGISTRY.get((source, target, connection_type))
    if exact is not None:
        return exact

    # Older payloads carried the API Gateway role inside connection_config
    role = config.get("connection_role")
    if role:
        by_role = CONNECTION_REGISTRY.get((source, target, role))
        if by_role is not None:
            return by_role

    candidates = [
        s for s in CONNECTION_SPECS if s.source == source and s.target == target
    ]
    if len(candidates) == 1:
        return candidates[0]
    return next((s for s in candidates if s.is_default), None)
