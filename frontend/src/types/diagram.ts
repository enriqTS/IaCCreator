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
  | 'text'
  | { type: 'place-service'; serviceType: ServiceType }
  | { type: 'place-shape'; shape: GeometricShape }
  | { type: 'place-uml'; umlKind: UMLKind };

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
  // CloudWatch
  retention_in_days?: number;
  kms_key_id?: string;
  log_group_class?: string;
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

// Connection anchor reference
export interface AnchorRef {
  objectId: string;
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
