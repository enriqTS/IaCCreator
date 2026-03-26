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
  | 'line'
  | { type: 'place-service'; serviceType: ServiceType }
  | { type: 'place-shape'; shape: GeometricShape };

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

// --- Canvas Object Type System ---

export type CanvasObjectType = 'architecture-block' | 'line' | 'geometric';
export type GeometricShape = 'rectangle' | 'ellipse';
export type StrokeStyle = 'solid' | 'dashed';

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
  position: Point;
  config: ResourceConfig;
  visualConfig: ArchitectureBlockVisualConfig;
}

export interface LineObject {
  id: string;
  objectType: 'line';
  name: string;
  start: Point;
  end: Point;
  visualConfig: LineVisualConfig;
}

export interface GeometricObject {
  id: string;
  objectType: 'geometric';
  name: string;
  position: Point;
  visualConfig: GeometricVisualConfig;
}

export type CanvasObject = ArchitectureBlock | LineObject | GeometricObject;

// Dimension constraints
export const MIN_OBJECT_WIDTH = 40;
export const MIN_OBJECT_HEIGHT = 40;

// Default visual configs
export const DEFAULT_BLOCK_VISUAL: ArchitectureBlockVisualConfig = {
  width: 80,
  height: 80,
};

export const DEFAULT_LINE_VISUAL: LineVisualConfig = {
  color: '#ffffff',
  borderWidth: 2,
  strokeStyle: 'solid',
  startArrow: false,
  endArrow: false,
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
