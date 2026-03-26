/**
 * Core diagram types and data models.
 * These mirror the design document interfaces and align with the backend's Pydantic schema.
 */

export type ServiceType =
  | 'lambda'
  | 's3'
  | 'api-gateway'
  | 'dynamodb'
  | 'iam'
  | 'cloudwatch';

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
}

export interface Viewport {
  offsetX: number;
  offsetY: number;
  scale: number; // 0.1 to 5.0
}

export type Tool =
  | 'pointer'
  | 'connector'
  | { type: 'place-service'; serviceType: ServiceType };

/** Service-specific configuration for a resource instance. Mirrors the backend ResourceConfig Pydantic schema. */
export interface ResourceConfig {
  // Lambda
  handler?: string;
  runtime?: string;
  memory_size?: number;
  timeout?: number;
  is_layer?: boolean;
  // S3
  versioning?: boolean;
  // DynamoDB
  billing_mode?: string;
  hash_key?: string;
  hash_key_type?: string;
  range_key?: string;
  range_key_type?: string;
  // API Gateway
  protocol_type?: string;
  // CloudWatch
  retention_in_days?: number;
}

export interface EnvironmentConfig {
  name: string;
  variables: Record<string, string>;
}
