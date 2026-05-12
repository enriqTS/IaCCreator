/**
 * Bundled copy of variable schemas — fallback when /api/variable-schemas is unreachable.
 * Generated from the same source of truth as the backend (app/generators/variable_schemas.py).
 *
 * Keep this in sync with the backend VARIABLE_SCHEMAS whenever schema definitions change.
 */

import type { ServiceVariableSchemas } from '@/types/terraform-variables';

export const BUNDLED_SCHEMAS: ServiceVariableSchemas = {
  lambda: [
    { name: 'function_name', type: 'string', description: 'Name of the Lambda function', group: 'General' },
    { name: 'handler', type: 'string', description: 'Lambda function handler (module.function)', default: 'lambda_function.lambda_handler', group: 'General' },
    {
      name: 'runtime', type: 'string', description: 'Lambda function runtime', default: 'python3.12', group: 'General',
      options: [
        { value: 'python3.12', label: 'Python 3.12', group: 'Python' },
        { value: 'python3.11', label: 'Python 3.11', group: 'Python' },
        { value: 'python3.10', label: 'Python 3.10', group: 'Python' },
        { value: 'python3.9', label: 'Python 3.9', group: 'Python' },
        { value: 'nodejs20.x', label: 'Node.js 20.x', group: 'Node.js' },
        { value: 'nodejs18.x', label: 'Node.js 18.x', group: 'Node.js' },
        { value: 'java21', label: 'Java 21', group: 'Java' },
        { value: 'java17', label: 'Java 17', group: 'Java' },
        { value: 'java11', label: 'Java 11', group: 'Java' },
        { value: 'dotnet8', label: '.NET 8', group: '.NET' },
        { value: 'dotnet6', label: '.NET 6', group: '.NET' },
        { value: 'ruby3.3', label: 'Ruby 3.3', group: 'Ruby' },
        { value: 'ruby3.2', label: 'Ruby 3.2', group: 'Ruby' },
        { value: 'provided.al2023', label: 'Custom Runtime (AL2023)', group: 'Custom' },
        { value: 'provided.al2', label: 'Custom Runtime (AL2)', group: 'Custom' },
      ],
    },
    { name: 'description', type: 'string', description: 'Description of the Lambda function', group: 'General' },
    { name: 'memory_size', type: 'number', description: 'Amount of memory available to the function at runtime (MB)', default: 128, group: 'Performance', validation: { min: 128, max: 10240 } },
    { name: 'timeout', type: 'number', description: 'Function execution timeout in seconds', default: 3, group: 'Performance', validation: { min: 1, max: 900 } },
    { name: 'ephemeral_storage_size', type: 'number', description: 'Size of the function /tmp directory in MB', default: 512, group: 'Performance', validation: { min: 512, max: 10240 } },
    { name: 'reserved_concurrent_executions', type: 'number', description: 'Number of reserved concurrent executions for this function', group: 'Performance', validation: { min: 0, max: 1000 } },
    {
      name: 'architectures', type: 'string', description: 'Instruction set architecture for the function', default: 'x86_64', group: 'Performance',
      options: [
        { value: 'x86_64', label: 'x86_64' },
        { value: 'arm64', label: 'ARM64 (Graviton2)' },
      ],
    },
    { name: 'publish', type: 'bool', description: 'Whether to publish creation/change as a new Lambda function version', default: false, group: 'Deployment' },
    { name: 'layers', type: 'list', description: 'List of Lambda layer ARNs to attach to the function', group: 'Deployment' },
    { name: 'environment_variables', type: 'map', description: 'Environment variables for the Lambda function', group: 'Metadata' },
    { name: 'tags', type: 'map', description: 'Tags to apply to the Lambda function', group: 'Metadata' },
  ],
  s3: [
    { name: 'bucket_name', type: 'string', description: 'Name of the S3 bucket', group: 'General' },
    {
      name: 'versioning', type: 'string', description: 'Versioning status for the S3 bucket', default: 'Enabled', group: 'General',
      options: [
        { value: 'Enabled', label: 'Enabled' },
        { value: 'Suspended', label: 'Suspended' },
        { value: 'Disabled', label: 'Disabled' },
      ],
    },
    { name: 'force_destroy', type: 'bool', description: 'Allow deletion of non-empty bucket by deleting all objects', default: false, group: 'Configuration' },
    { name: 'object_lock_enabled', type: 'bool', description: 'Enable S3 Object Lock on the bucket', default: false, group: 'Configuration' },
    {
      name: 'acceleration_status', type: 'string', description: 'Transfer acceleration status for the bucket', group: 'Configuration',
      options: [
        { value: 'Enabled', label: 'Enabled' },
        { value: 'Suspended', label: 'Suspended' },
      ],
    },
    { name: 'tags', type: 'map', description: 'Tags to apply to the S3 bucket', group: 'Metadata' },
  ],
  dynamodb: [
    { name: 'table_name', type: 'string', description: 'Name of the DynamoDB table', group: 'General' },
    {
      name: 'billing_mode', type: 'string', description: 'Billing mode for read/write throughput', default: 'PAY_PER_REQUEST', group: 'General',
      options: [
        { value: 'PAY_PER_REQUEST', label: 'On-Demand (PAY_PER_REQUEST)' },
        { value: 'PROVISIONED', label: 'Provisioned' },
      ],
    },
    {
      name: 'table_class', type: 'string', description: 'Storage class for the DynamoDB table', default: 'STANDARD', group: 'General',
      options: [
        { value: 'STANDARD', label: 'Standard' },
        { value: 'STANDARD_INFREQUENT_ACCESS', label: 'Standard - Infrequent Access' },
      ],
    },
    { name: 'hash_key', type: 'string', description: 'Attribute name for the partition (hash) key', group: 'Key Schema' },
    {
      name: 'hash_key_type', type: 'string', description: 'Attribute type for the partition (hash) key', default: 'S', group: 'Key Schema',
      options: [
        { value: 'S', label: 'String' },
        { value: 'N', label: 'Number' },
        { value: 'B', label: 'Binary' },
      ],
    },
    { name: 'range_key', type: 'string', description: 'Attribute name for the sort (range) key', group: 'Key Schema' },
    {
      name: 'range_key_type', type: 'string', description: 'Attribute type for the sort (range) key', default: 'S', group: 'Key Schema',
      options: [
        { value: 'S', label: 'String' },
        { value: 'N', label: 'Number' },
        { value: 'B', label: 'Binary' },
      ],
    },
    { name: 'read_capacity', type: 'number', description: 'Provisioned read capacity units', default: 5, group: 'Capacity', validation: { min: 1, max: 40000 }, visible_when: { field: 'billing_mode', equals: 'PROVISIONED' } },
    { name: 'write_capacity', type: 'number', description: 'Provisioned write capacity units', default: 5, group: 'Capacity', validation: { min: 1, max: 40000 }, visible_when: { field: 'billing_mode', equals: 'PROVISIONED' } },
    { name: 'tags', type: 'map', description: 'Tags to apply to the DynamoDB table', group: 'Metadata' },
    { name: 'point_in_time_recovery_enabled', type: 'bool', description: 'Enable point-in-time recovery for the table', default: false, group: 'Metadata' },
    { name: 'deletion_protection_enabled', type: 'bool', description: 'Enable deletion protection for the table', default: false, group: 'Metadata' },
  ],
  'api-gateway': [
    // ─── General ───────────────────────────────────────────────────
    { name: 'api_name', type: 'string', description: 'Name of the API Gateway', group: 'General' },
    {
      name: 'protocol_type', type: 'string', description: 'API protocol type', default: 'HTTP', group: 'General',
      options: [
        { value: 'HTTP', label: 'HTTP' },
        { value: 'WEBSOCKET', label: 'WebSocket' },
        { value: 'REST', label: 'REST' },
      ],
    },
    { name: 'description', type: 'string', description: 'Description of the API', group: 'General' },
    // ─── Routes ───────────────────────────────────────────────────
    {
      name: 'route_method', type: 'string', description: 'HTTP method for the route', default: 'ANY', group: 'Routes',
      options: [
        { value: 'GET', label: 'GET' },
        { value: 'POST', label: 'POST' },
        { value: 'PUT', label: 'PUT' },
        { value: 'DELETE', label: 'DELETE' },
        { value: 'PATCH', label: 'PATCH' },
        { value: 'HEAD', label: 'HEAD' },
        { value: 'OPTIONS', label: 'OPTIONS' },
        { value: 'ANY', label: 'ANY' },
      ],
    },
    { name: 'route_path', type: 'string', description: 'Route path (e.g., /users/{id})', group: 'Routes' },
    { name: 'route_selection_expression', type: 'string', description: 'Route selection expression for WebSocket APIs', group: 'Routes', visible_when: { field: 'protocol_type', equals: 'WEBSOCKET' } },
    // ─── Stages ───────────────────────────────────────────────────
    { name: 'stage_name', type: 'string', description: 'Name of the deployment stage (e.g., $default, dev, prod)', group: 'Stages' },
    { name: 'auto_deploy', type: 'bool', description: 'Whether to auto-deploy changes to this stage', default: true, group: 'Stages' },
    { name: 'stage_variables', type: 'map', description: 'Stage variables as key-value pairs (max 50 entries)', group: 'Stages' },
    // ─── Authorizers ──────────────────────────────────────────────
    {
      name: 'authorizer_type', type: 'string', description: 'Type of authorizer to attach to the API', group: 'Authorizers',
      options: [
        { value: 'JWT', label: 'JWT' },
        { value: 'REQUEST', label: 'Lambda (REQUEST)' },
        { value: 'COGNITO_USER_POOLS', label: 'Cognito User Pools' },
      ],
    },
    { name: 'jwt_issuer', type: 'string', description: 'Issuer URL for the JWT authorizer', group: 'Authorizers', visible_when: { field: 'authorizer_type', equals: 'JWT' } },
    { name: 'jwt_audience', type: 'string', description: 'Audience value(s) for the JWT authorizer', group: 'Authorizers', visible_when: { field: 'authorizer_type', equals: 'JWT' } },
    { name: 'lambda_authorizer_uri', type: 'string', description: 'Lambda function invoke ARN for the REQUEST authorizer', group: 'Authorizers', visible_when: { field: 'authorizer_type', equals: 'REQUEST' } },
    {
      name: 'authorizer_payload_format_version', type: 'string', description: 'Payload format version for the Lambda authorizer', group: 'Authorizers',
      visible_when: { field: 'authorizer_type', equals: 'REQUEST' },
      options: [
        { value: '1.0', label: '1.0' },
        { value: '2.0', label: '2.0' },
      ],
    },
    { name: 'cognito_user_pool_endpoint', type: 'string', description: 'Cognito User Pool endpoint URL', group: 'Authorizers', visible_when: { field: 'authorizer_type', equals: 'COGNITO_USER_POOLS' } },
    { name: 'cognito_client_ids', type: 'list', description: 'List of Cognito User Pool client IDs', group: 'Authorizers', visible_when: { field: 'authorizer_type', equals: 'COGNITO_USER_POOLS' } },
    // ─── Custom Domain ────────────────────────────────────────────
    { name: 'custom_domain_name', type: 'string', description: 'Custom domain name for the API (e.g., api.example.com)', group: 'Custom Domain' },
    { name: 'certificate_arn', type: 'string', description: 'ARN of the ACM certificate for the custom domain', group: 'Custom Domain' },
    // ─── Integrations ─────────────────────────────────────────────
    {
      name: 'integration_type', type: 'string', description: 'Type of backend integration', group: 'Integrations',
      options: [
        { value: 'AWS_PROXY', label: 'AWS Lambda (AWS_PROXY)' },
        { value: 'HTTP_PROXY', label: 'HTTP Proxy (HTTP_PROXY)' },
        { value: 'HTTP', label: 'HTTP Custom (HTTP)' },
      ],
    },
    { name: 'integration_uri', type: 'string', description: 'URI of the integration target', group: 'Integrations' },
    { name: 'integration_method', type: 'string', description: 'HTTP method for the integration (required for HTTP_PROXY and HTTP)', group: 'Integrations', visible_when: { field: 'integration_type', equals: 'HTTP_PROXY' } },
    // ─── Rate Limiting ────────────────────────────────────────────
    { name: 'throttling_burst_limit', type: 'number', description: 'Maximum number of concurrent requests (burst)', group: 'Rate Limiting', validation: { min: 1, max: 5000 } },
    { name: 'throttling_rate_limit', type: 'number', description: 'Maximum number of requests per second (steady-state)', group: 'Rate Limiting', validation: { min: 1, max: 10000 } },
    // ─── VPC Link ─────────────────────────────────────────────────
    { name: 'vpc_link_name', type: 'string', description: 'Name of the VPC link for private integrations', group: 'VPC Link' },
    { name: 'vpc_link_subnet_ids', type: 'list', description: 'List of subnet IDs for the VPC link (1-3 entries)', group: 'VPC Link' },
    { name: 'vpc_link_security_group_ids', type: 'list', description: 'List of security group IDs for the VPC link (1-5 entries)', group: 'VPC Link' },
    // ─── Metadata ─────────────────────────────────────────────────
    { name: 'cors_configuration', type: 'map', description: 'CORS configuration for the API', group: 'Metadata' },
    { name: 'disable_execute_api_endpoint', type: 'bool', description: 'Disable the default execute-api endpoint', default: false, group: 'Metadata' },
    { name: 'api_key_required', type: 'bool', description: 'Whether API key is required for routes', default: false, group: 'Metadata' },
    { name: 'tags', type: 'map', description: 'Tags to apply to the API Gateway', group: 'Metadata' },
  ],
  cloudwatch: [
    { name: 'log_group_name', type: 'string', description: 'Name of the CloudWatch log group', group: 'General' },
    {
      name: 'retention_in_days', type: 'number', description: 'Number of days to retain log events', default: 30, group: 'General',
      options: [
        { value: 0, label: 'Never expire' },
        { value: 1, label: '1 day' },
        { value: 3, label: '3 days' },
        { value: 5, label: '5 days' },
        { value: 7, label: '1 week' },
        { value: 14, label: '2 weeks' },
        { value: 30, label: '1 month' },
        { value: 60, label: '2 months' },
        { value: 90, label: '3 months' },
        { value: 120, label: '4 months' },
        { value: 150, label: '5 months' },
        { value: 180, label: '6 months' },
        { value: 365, label: '1 year' },
        { value: 400, label: '13 months' },
        { value: 545, label: '18 months' },
        { value: 731, label: '2 years' },
        { value: 1096, label: '3 years' },
        { value: 1827, label: '5 years' },
        { value: 2192, label: '6 years' },
        { value: 2557, label: '7 years' },
        { value: 2922, label: '8 years' },
        { value: 3288, label: '9 years' },
        { value: 3653, label: '10 years' },
      ],
      validation: {
        allowed_values: [0, 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653],
      },
    },
    { name: 'kms_key_id', type: 'string', description: 'ARN of the KMS key to use for encrypting log data', group: 'Configuration' },
    {
      name: 'log_group_class', type: 'string', description: 'Log group class for the CloudWatch log group', default: 'STANDARD', group: 'Configuration',
      options: [
        { value: 'STANDARD', label: 'Standard' },
        { value: 'INFREQUENT_ACCESS', label: 'Infrequent Access' },
      ],
    },
    { name: 'tags', type: 'map', description: 'Tags to apply to the CloudWatch log group', group: 'Metadata' },
  ],
  ec2: [
    { name: 'instance_name', type: 'string', description: 'Name tag for the EC2 instance', group: 'General' },
    { name: 'ami', type: 'string', description: 'AMI ID for the instance', group: 'General' },
    { name: 'instance_type', type: 'string', description: 'EC2 instance type', default: 't3.micro', group: 'General' },
  ],
  ecs: [
    { name: 'cluster_name', type: 'string', description: 'Name of the ECS cluster', group: 'General' },
    { name: 'task_family', type: 'string', description: 'Family name for the ECS task definition', group: 'General' },
    { name: 'ecs_cpu', type: 'string', description: 'CPU units for the ECS task', default: '256', group: 'Performance' },
    { name: 'ecs_memory', type: 'string', description: 'Memory (MiB) for the ECS task', default: '512', group: 'Performance' },
  ],
  eks: [
    { name: 'cluster_name', type: 'string', description: 'Name of the EKS cluster', group: 'General' },
    { name: 'cluster_role_arn', type: 'string', description: 'ARN of the IAM role for the EKS cluster', group: 'General' },
    { name: 'subnet_ids', type: 'list', description: 'List of subnet IDs for the EKS cluster VPC config', group: 'Networking' },
  ],
  'elastic-beanstalk': [
    { name: 'application_name', type: 'string', description: 'Name of the Elastic Beanstalk application', group: 'General' },
    { name: 'environment_name', type: 'string', description: 'Name of the Elastic Beanstalk environment', group: 'General' },
  ],
  'app-runner': [
    { name: 'service_name', type: 'string', description: 'Name of the App Runner service', group: 'General' },
    { name: 'image_identifier', type: 'string', description: 'Container image identifier for the App Runner service', group: 'General' },
  ],
  batch: [
    { name: 'compute_environment_name', type: 'string', description: 'Name of the Batch compute environment', group: 'General' },
    { name: 'service_role_arn', type: 'string', description: 'ARN of the IAM service role for Batch', group: 'General' },
  ],
  'ec2-image-builder': [
    { name: 'pipeline_name', type: 'string', description: 'Name of the Image Builder pipeline', group: 'General' },
    { name: 'image_recipe_arn', type: 'string', description: 'ARN of the image recipe', group: 'General' },
    { name: 'infrastructure_configuration_arn', type: 'string', description: 'ARN of the infrastructure configuration', group: 'General' },
  ],
  lightsail: [
    { name: 'instance_name', type: 'string', description: 'Name of the Lightsail instance', group: 'General' },
    { name: 'blueprint_id', type: 'string', description: 'Blueprint ID for the Lightsail instance', group: 'General' },
    { name: 'bundle_id', type: 'string', description: 'Bundle ID for the Lightsail instance', group: 'General' },
    { name: 'availability_zone', type: 'string', description: 'Availability zone for the Lightsail instance', group: 'General' },
  ],
  ecr: [
    { name: 'repository_name', type: 'string', description: 'Name of the ECR repository', group: 'General' },
  ],
  // Analytics
  athena: [
    { name: 'workgroup_name', type: 'string', description: 'Name of the Athena workgroup', group: 'General' },
  ],
  cloudsearch: [
    { name: 'domain_name', type: 'string', description: 'Name of the CloudSearch domain', group: 'General' },
  ],
  emr: [
    { name: 'cluster_name', type: 'string', description: 'Name of the EMR cluster', group: 'General' },
    { name: 'release_label', type: 'string', description: 'EMR release label', group: 'General' },
    { name: 'service_role', type: 'string', description: 'IAM service role for the EMR cluster', group: 'General' },
  ],
  glue: [
    { name: 'database_name', type: 'string', description: 'Name of the Glue catalog database', group: 'General' },
  ],
  kinesis: [
    { name: 'stream_name', type: 'string', description: 'Name of the Kinesis stream', group: 'General' },
    { name: 'shard_count', type: 'number', description: 'Number of shards for the Kinesis stream', group: 'General' },
  ],
  'kinesis-firehose': [
    { name: 'stream_name', type: 'string', description: 'Name of the Firehose delivery stream', group: 'General' },
    { name: 'destination', type: 'string', description: 'Destination for the Firehose delivery stream', group: 'General' },
  ],
  msk: [
    { name: 'cluster_name', type: 'string', description: 'Name of the MSK cluster', group: 'General' },
    { name: 'kafka_version', type: 'string', description: 'Apache Kafka version for the MSK cluster', group: 'General' },
    { name: 'number_of_broker_nodes', type: 'number', description: 'Number of broker nodes in the MSK cluster', group: 'General' },
  ],
  opensearch: [
    { name: 'domain_name', type: 'string', description: 'Name of the OpenSearch domain', group: 'General' },
  ],
  redshift: [
    { name: 'cluster_identifier', type: 'string', description: 'Identifier for the Redshift cluster', group: 'General' },
    { name: 'node_type', type: 'string', description: 'Node type for the Redshift cluster', group: 'General' },
    { name: 'master_username', type: 'string', description: 'Master username for the Redshift cluster', group: 'General' },
  ],
  // Business Applications
  connect: [
    { name: 'identity_management_type', type: 'string', description: 'Identity management type for the Connect instance', group: 'General' },
    { name: 'inbound_calls_enabled', type: 'bool', description: 'Whether inbound calls are enabled', group: 'General' },
    { name: 'outbound_calls_enabled', type: 'bool', description: 'Whether outbound calls are enabled', group: 'General' },
  ],
  ses: [
    { name: 'domain', type: 'string', description: 'Domain name for SES identity', group: 'General' },
  ],
  pinpoint: [
    { name: 'app_name', type: 'string', description: 'Name of the Pinpoint application', group: 'General' },
  ],
  // Database
  aurora: [
    { name: 'cluster_identifier', type: 'string', description: 'Identifier for the Aurora cluster', group: 'General' },
    { name: 'engine', type: 'string', description: 'Database engine for the Aurora cluster', group: 'General' },
    { name: 'master_username', type: 'string', description: 'Master username for the Aurora cluster', group: 'General' },
  ],
  documentdb: [
    { name: 'cluster_identifier', type: 'string', description: 'Identifier for the DocumentDB cluster', group: 'General' },
    { name: 'master_username', type: 'string', description: 'Master username for the DocumentDB cluster', group: 'General' },
  ],
  elasticache: [
    { name: 'cluster_id', type: 'string', description: 'Identifier for the ElastiCache cluster', group: 'General' },
    { name: 'engine', type: 'string', description: 'Cache engine type', group: 'General' },
    { name: 'node_type', type: 'string', description: 'ElastiCache node type', group: 'General' },
    { name: 'num_cache_nodes', type: 'number', description: 'Number of cache nodes in the cluster', group: 'General' },
  ],
  neptune: [
    { name: 'cluster_identifier', type: 'string', description: 'Identifier for the Neptune cluster', group: 'General' },
  ],
  rds: [
    { name: 'db_identifier', type: 'string', description: 'Identifier for the RDS instance', group: 'General' },
    { name: 'engine', type: 'string', description: 'Database engine type', group: 'General' },
    { name: 'instance_class', type: 'string', description: 'RDS instance class', default: 'db.t3.micro', group: 'General' },
    { name: 'allocated_storage', type: 'number', description: 'Allocated storage in GB', default: 20, group: 'General' },
    { name: 'username', type: 'string', description: 'Master username for the database', group: 'General' },
  ],
  timestream: [
    { name: 'database_name', type: 'string', description: 'Name of the Timestream database', group: 'General' },
  ],
  // Developer Tools
  codebuild: [
    { name: 'project_name', type: 'string', description: 'Name of the CodeBuild project', group: 'General' },
    { name: 'service_role', type: 'string', description: 'IAM service role ARN for CodeBuild', group: 'General' },
    { name: 'source_type', type: 'string', description: 'Source type for the CodeBuild project', group: 'General' },
  ],
  codecommit: [
    { name: 'repository_name', type: 'string', description: 'Name of the CodeCommit repository', group: 'General' },
  ],
  codedeploy: [
    { name: 'app_name', type: 'string', description: 'Name of the CodeDeploy application', group: 'General' },
    { name: 'compute_platform', type: 'string', description: 'Compute platform for CodeDeploy', group: 'General' },
  ],
  codepipeline: [
    { name: 'pipeline_name', type: 'string', description: 'Name of the CodePipeline pipeline', group: 'General' },
    { name: 'role_arn', type: 'string', description: 'IAM role ARN for CodePipeline', group: 'General' },
  ],
  // End User Computing
  appstream: [
    { name: 'fleet_name', type: 'string', description: 'Name of the AppStream fleet', group: 'General' },
    { name: 'instance_type', type: 'string', description: 'Instance type for the AppStream fleet', group: 'General' },
  ],
  // Front End Web Mobile
  amplify: [
    { name: 'app_name', type: 'string', description: 'Name of the Amplify application', group: 'General' },
  ],
  // Games
  gamelift: [
    { name: 'fleet_name', type: 'string', description: 'Name of the GameLift fleet', group: 'General' },
    { name: 'ec2_instance_type', type: 'string', description: 'EC2 instance type for the GameLift fleet', group: 'General' },
  ],
};
