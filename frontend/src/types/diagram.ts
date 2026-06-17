/**
 * Core diagram types and data models.
 * These mirror the design document interfaces and align with the backend's Pydantic schema.
 */

import type { AnchorPosition } from '@/utils/anchor';

export type ServiceType =
  | 'lambda'
  | 's3'
  | 'api-gateway'
  | 'dynamodb'
  | 'iam'
  | 'cloudwatch'
  | 'sns'
  | 'sqs'
  // Compute — full-generator services
  | 'ec2'
  | 'elastic-beanstalk'
  | 'app-runner'
  | 'batch'
  | 'ec2-image-builder'
  | 'lightsail'
  // Containers — full-generator services
  | 'ecs'
  | 'eks'
  | 'ecr'
  // Compute — icon-only services
  | 'application-auto-scaling'
  | 'bottlerocket'
  | 'compute-optimizer'
  | 'ec2-auto-scaling'
  | 'elastic-fabric-adapter'
  | 'fargate'
  | 'genomics-cli'
  | 'local-zones'
  | 'nice-dcv'
  | 'nice-enginframe'
  | 'nitro-enclaves'
  | 'outposts-family'
  | 'outposts-rack'
  | 'outposts-servers'
  | 'parallelcluster'
  | 'serverless-application-repository'
  | 'simspace-weaver'
  | 'thinkbox-deadline'
  | 'thinkbox-frost'
  | 'thinkbox-krakatoa'
  | 'thinkbox-sequoia'
  | 'thinkbox-stoke'
  | 'thinkbox-xmesh'
  | 'vmware-cloud-on-aws'
  | 'wavelength'
  // Containers — icon-only services
  | 'ecs-anywhere'
  | 'eks-anywhere'
  | 'eks-cloud'
  | 'eks-distro'
  | 'red-hat-openshift'
  // Analytics — full-generator services
  | 'athena'
  | 'cloudsearch'
  | 'emr'
  | 'glue'
  | 'kinesis'
  | 'kinesis-firehose'
  | 'msk'
  | 'opensearch'
  | 'redshift'
  // Analytics — icon-only services
  | 'clean-rooms'
  | 'data-exchange'
  | 'data-pipeline'
  | 'datazone'
  | 'finspace'
  | 'glue-databrew'
  | 'glue-elastic-views'
  | 'kinesis-data-analytics'
  | 'kinesis-data-streams'
  | 'kinesis-video-streams'
  | 'lake-formation'
  | 'quicksight'
  // Blockchain — icon-only services
  | 'managed-blockchain'
  | 'quantum-ledger-database'
  // Business Applications — full-generator services
  | 'connect'
  | 'ses'
  | 'pinpoint'
  // Business Applications — icon-only services
  | 'alexa-for-business'
  | 'chime-sdk'
  | 'chime-voice-connector'
  | 'chime'
  | 'honeycode'
  | 'pinpoint-apis'
  | 'supply-chain'
  | 'wickr'
  | 'workdocs-sdk'
  | 'workdocs'
  | 'workmail'
  // Cloud Financial Management — icon-only services
  | 'application-cost-profiler'
  | 'billing-conductor'
  | 'budgets'
  | 'cost-and-usage-report'
  | 'cost-explorer'
  | 'reserved-instance-reporting'
  | 'savings-plans'
  // Customer Enablement — icon-only services
  | 'activate'
  | 'iq'
  | 'managed-services'
  | 'professional-services'
  | 'repost'
  | 'support'
  | 'training-certification'
  // Database — full-generator services
  | 'aurora'
  | 'documentdb'
  | 'elasticache'
  | 'neptune'
  | 'rds'
  | 'timestream'
  // Database — icon-only services
  | 'database-migration-service'
  | 'keyspaces'
  | 'memorydb'
  | 'rds-on-vmware'
  // Developer Tools — full-generator services
  | 'codebuild'
  | 'codecommit'
  | 'codedeploy'
  | 'codepipeline'
  // Developer Tools — icon-only services
  | 'application-composer'
  | 'cloud-control-api'
  | 'cloud-development-kit'
  | 'cloud9'
  | 'cloudshell'
  | 'codeartifact'
  | 'codecatalyst'
  | 'codestar'
  | 'command-line-interface'
  | 'corretto'
  | 'tools-and-sdks'
  | 'x-ray'
  // End User Computing — full-generator services
  | 'appstream'
  // End User Computing — icon-only services
  | 'worklink'
  | 'workspaces-family'
  // Front End Web Mobile — full-generator services
  | 'amplify'
  // Front End Web Mobile — icon-only services
  | 'device-farm'
  | 'location-service'
  // Games — full-generator services
  | 'gamelift'
  // Games — icon-only services
  | 'gamekit'
  | 'gamesparks'
  | 'lumberyard'
  | 'open-3d-engine'
  // Machine Learning — full-generator services
  | 'bedrock'
  | 'sagemaker'
  | 'amazon-q'
  | 'bedrock-agent'
  | 'bedrock-guardrail'
  | 'bedrock-knowledge-base'
  | 'bedrock-agentcore';

export interface Point {
  x: number;
  y: number;
}

export interface DiagramElement {
  id: string;
  serviceType: ServiceType;
  name: string;
  position: Point;
  config: ResourceConfig;
}

export interface Connector {
  id: string;
  sourceId: string;
  targetId: string;
  connectionType: string;
  connectionConfig?: Record<string, string | number | boolean>;
}

export interface Viewport {
  offsetX: number;
  offsetY: number;
  scale: number; // 0.1 to 5.0
}

export type Tool =
  | 'pointer'
  | 'connector'
  | 'line'
  | 'text'
  | { type: 'place-service'; serviceType: ServiceType }
  | { type: 'place-shape'; shape: GeometricShape }
  | { type: 'place-uml'; umlKind: UMLKind }
  | { type: 'place-line' };

/** Service-specific configuration for a resource instance. Mirrors the backend ResourceConfig Pydantic schema. */
export interface ResourceConfig {
  // Lambda
  handler?: string;
  runtime?: string;
  memory_size?: number;
  timeout?: number;
  is_layer?: boolean;
  description?: string;
  environment_variables?: Record<string, string>;
  tags?: Record<string, string>;
  layers?: string[];
  architectures?: string;
  ephemeral_storage_size?: number;
  reserved_concurrent_executions?: number;
  publish?: boolean;
  // S3
  versioning?: boolean;
  force_destroy?: boolean;
  object_lock_enabled?: boolean;
  acceleration_status?: string;
  // DynamoDB
  billing_mode?: string;
  hash_key?: string;
  hash_key_type?: string;
  range_key?: string;
  range_key_type?: string;
  read_capacity?: number;
  write_capacity?: number;
  point_in_time_recovery_enabled?: boolean;
  deletion_protection_enabled?: boolean;
  table_class?: string;
  // API Gateway
  protocol_type?: string;
  cors_configuration?: Record<string, unknown>;
  disable_execute_api_endpoint?: boolean;
  route_selection_expression?: string;
  routes?: Record<string, unknown>[];
  // CloudWatch
  retention_in_days?: number;
  kms_key_id?: string;
  log_group_class?: string;
  // SNS
  display_name?: string;
  fifo_topic?: boolean;
  content_based_deduplication?: boolean;
  kms_master_key_id?: string;
  // SQS
  visibility_timeout_seconds?: number;
  message_retention_seconds?: number;
  fifo_queue?: boolean;
  delay_seconds?: number;
  max_message_size?: number;
  // EC2
  instance_type?: string;
  ami?: string;
  key_name?: string;
  // ECS
  ecs_launch_type?: string;
  ecs_desired_count?: number;
  ecs_cpu?: string;
  ecs_memory?: string;
  // EKS
  eks_version?: string;
  eks_endpoint_public_access?: boolean;
  // Elastic Beanstalk
  eb_solution_stack_name?: string;
  eb_tier?: string;
  // App Runner
  apprunner_source_type?: string;
  apprunner_image_identifier?: string;
  // Batch
  batch_compute_environment_type?: string;
  batch_max_vcpus?: number;
  // EC2 Image Builder
  imagebuilder_image_recipe_arn?: string;
  imagebuilder_infrastructure_configuration_arn?: string;
  // Lightsail
  lightsail_blueprint_id?: string;
  lightsail_bundle_id?: string;
  lightsail_availability_zone?: string;
  // ECR
  ecr_image_tag_mutability?: string;
  ecr_scan_on_push?: boolean;
  // Analytics
  athena_name?: string;
  cloudsearch_name?: string;
  emr_release_label?: string;
  emr_service_role?: string;
  glue_catalog_database_name?: string;
  kinesis_shard_count?: number;
  firehose_destination?: string;
  msk_kafka_version?: string;
  msk_number_of_broker_nodes?: number;
  opensearch_domain_name?: string;
  redshift_node_type?: string;
  redshift_master_username?: string;
  // Business Applications
  connect_identity_management_type?: string;
  connect_inbound_calls_enabled?: boolean;
  connect_outbound_calls_enabled?: boolean;
  ses_domain?: string;
  pinpoint_name?: string;
  // Database
  aurora_engine?: string;
  aurora_master_username?: string;
  documentdb_master_username?: string;
  elasticache_engine?: string;
  elasticache_node_type?: string;
  elasticache_num_cache_nodes?: number;
  neptune_cluster_identifier?: string;
  rds_engine?: string;
  rds_instance_class?: string;
  rds_allocated_storage?: number;
  rds_username?: string;
  timestream_database_name?: string;
  // Developer Tools
  codebuild_source_type?: string;
  codebuild_service_role?: string;
  codecommit_repository_name?: string;
  codedeploy_compute_platform?: string;
  codepipeline_role_arn?: string;
  // End User Computing
  appstream_instance_type?: string;
  // Front End Web Mobile
  amplify_name?: string;
  // Games
  gamelift_ec2_instance_type?: string;
  // Machine Learning / AI
  bedrock_model_name?: string;
  bedrock_base_model_identifier?: string;
  sagemaker_notebook_instance_name?: string;
  sagemaker_instance_type?: string;
  amazon_q_application_name?: string;
  bedrock_agent_name?: string;
  bedrock_agent_foundation_model?: string;
  bedrock_agent_instruction?: string;
  bedrock_knowledge_base_name?: string;
  bedrock_knowledge_base_embedding_model_arn?: string;
  bedrock_guardrail_name?: string;
}

export interface EnvironmentConfig {
  name: string;
  variables: Record<string, string>;
}

// --- Canvas Object Type System ---

export type CanvasObjectType = 'architecture-block' | 'line' | 'geometric' | 'text' | 'uml';

export type GeometricShape =
  | 'rectangle' | 'rounded-rectangle' | 'ellipse' | 'circle'
  | 'triangle' | 'diamond' | 'parallelogram' | 'trapezoid'
  | 'hexagon' | 'octagon' | 'pentagon' | 'star' | 'cross'
  | 'arrow-right' | 'arrow-left' | 'arrow-up' | 'arrow-down'
  | 'chevron' | 'cylinder' | 'cloud' | 'callout'
  | 'document' | 'process' | 'decision' | 'data' | 'predefined-process';

export type UMLKind = 'class' | 'interface' | 'actor' | 'use-case' | 'component' | 'package' | 'node';

export type StrokeStyle = 'solid' | 'dashed';

export type RoutingMode = 'orthogonal' | 'diagonal';

// Connection anchor reference
export interface AnchorRef {
  objectId: string;
  anchorPosition: AnchorPosition;
}

// Text visual config
export interface TextVisualConfig {
  width: number;
  height: number;
  fontSize: number;
  fontColor: string;
  textAlign: 'left' | 'center' | 'right';
  bold: boolean;
  italic: boolean;
}

// UML visual config
export interface UMLVisualConfig {
  width: number;
  height: number;
  fillColor: string;
  borderColor: string;
  borderWidth: number;
  headerColor: string;
}

// UML compartment data
export interface UMLClassData {
  stereotype?: string;
  attributes: string[];
  methods: string[];
}

// Visual config per object type
export interface ArchitectureBlockVisualConfig {
  width: number;
  height: number;
}

export interface LineVisualConfig {
  color: string;
  borderWidth: number;
  strokeStyle: StrokeStyle;
  startArrow: boolean;
  endArrow: boolean;
  routingMode: RoutingMode;
}

export interface GeometricVisualConfig {
  width: number;
  height: number;
  fill: boolean;
  fillColor: string;
  borderColor: string;
  borderWidth: number;
  shape: GeometricShape;
}

// Canvas object interfaces (discriminated union on objectType)
export interface ArchitectureBlock {
  id: string;
  objectType: 'architecture-block';
  serviceType: ServiceType;
  name: string;
  /** The originally generated default name, preserved for revert behavior. */
  defaultName?: string;
  position: Point;
  config: ResourceConfig;
  terraformVariables: Record<string, string | number | boolean>;
  visualConfig: ArchitectureBlockVisualConfig;
  zIndex: number;
  groupId?: string;
  locked?: boolean;
}

export interface LineObject {
  id: string;
  objectType: 'line';
  name: string;
  start: Point;
  end: Point;
  sourceAnchor: AnchorRef | null;
  targetAnchor: AnchorRef | null;
  waypoints?: Point[] | null;
  visualConfig: LineVisualConfig;
  zIndex: number;
  groupId?: string;
  locked?: boolean;
}

export interface GeometricObject {
  id: string;
  objectType: 'geometric';
  name: string;
  position: Point;
  visualConfig: GeometricVisualConfig;
  zIndex: number;
  groupId?: string;
  locked?: boolean;
}

export interface TextObject {
  id: string;
  objectType: 'text';
  name: string;
  position: Point;
  content: string;
  visualConfig: TextVisualConfig;
  zIndex: number;
  groupId?: string;
  locked?: boolean;
}

export interface UMLObject {
  id: string;
  objectType: 'uml';
  name: string;
  position: Point;
  umlKind: UMLKind;
  classData?: UMLClassData;
  visualConfig: UMLVisualConfig;
  zIndex: number;
  groupId?: string;
  locked?: boolean;
}

// Object group
export interface ObjectGroup {
  id: string;
  name: string;
  memberIds: string[];
}

// Axis-aligned bounding rectangle
export interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export type CanvasObject = ArchitectureBlock | LineObject | GeometricObject | TextObject | UMLObject;

/** Distributive Omit that works correctly with discriminated unions */
export type CanvasObjectCreationPayload =
  | Omit<ArchitectureBlock, 'id' | 'zIndex'>
  | Omit<LineObject, 'id' | 'zIndex'>
  | Omit<GeometricObject, 'id' | 'zIndex'>
  | Omit<TextObject, 'id' | 'zIndex'>
  | Omit<UMLObject, 'id' | 'zIndex'>;

// Dimension constraints
export const MIN_OBJECT_WIDTH = 40;
export const MIN_OBJECT_HEIGHT = 40;

// Default visual configs
export const DEFAULT_BLOCK_VISUAL: ArchitectureBlockVisualConfig = {
  width: 80,
  height: 80,
};

/**
 * Default visual config for lines. The 'orthogonal' routingMode is the default
 * for Connector tool connections between Architecture_Blocks.
 * Lines placed from the Object Picker override this to 'diagonal' (freeform routing)
 * at creation time — see Canvas.tsx line placement logic.
 */
export const DEFAULT_LINE_VISUAL: LineVisualConfig = {
  color: '#ffffff',
  borderWidth: 2,
  strokeStyle: 'solid',
  startArrow: false,
  endArrow: false,
  routingMode: 'orthogonal',
};

export const DEFAULT_GEO_VISUAL: GeometricVisualConfig = {
  width: 120,
  height: 80,
  fill: false,
  fillColor: '#3b82f6',
  borderColor: '#ffffff',
  borderWidth: 2,
  shape: 'rectangle',
};

export const DEFAULT_TEXT_VISUAL: TextVisualConfig = {
  width: 50,
  height: 28,
  fontSize: 14,
  fontColor: '#ffffff',
  textAlign: 'center',
  bold: false,
  italic: false,
};

export const DEFAULT_UML_VISUAL: UMLVisualConfig = {
  width: 180,
  height: 120,
  fillColor: '#2a2a2a',
  borderColor: '#ffffff',
  borderWidth: 2,
  headerColor: '#3b82f6',
};

export const DEFAULT_UML_CLASS_DATA: UMLClassData = {
  attributes: [],
  methods: [],
};

/** Compute the axis-aligned bounding box for any CanvasObject. */
export function getObjectBounds(obj: CanvasObject): Rect {
  if (obj.objectType === 'line') {
    const minX = Math.min(obj.start.x, obj.end.x);
    const minY = Math.min(obj.start.y, obj.end.y);
    return {
      x: minX,
      y: minY,
      width: Math.abs(obj.end.x - obj.start.x),
      height: Math.abs(obj.end.y - obj.start.y),
    };
  }
  // architecture-block, geometric, text, and uml: position is center
  const vc = obj.visualConfig as { width: number; height: number };
  return {
    x: obj.position.x - vc.width / 2,
    y: obj.position.y - vc.height / 2,
    width: vc.width,
    height: vc.height,
  };
}
