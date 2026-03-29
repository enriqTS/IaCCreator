/**
 * Serialization types for save/load and backend API export.
 */

import type {
  CanvasObjectType,
  EnvironmentConfig,
  Point,
  ResourceConfig,
  ServiceType,
  UMLClassData,
  UMLKind,
  Viewport,
} from './diagram';
import type { GlobalTerraformConfig } from './terraform-variables';

/** Current serialization format version. */
export const CURRENT_DIAGRAM_VERSION = 3;

/** Full diagram state for save/load to localStorage. */
export interface DiagramState {
  version: number;
  projectName: string;
  environments: EnvironmentConfig[];
  elements: SerializedElement[];
  canvasObjects?: SerializedCanvasObject[];
  connectors: SerializedConnector[];
  viewport: Viewport;
  objectGroups?: SerializedObjectGroup[];
  globalTerraformConfig?: GlobalTerraformConfig;
  globalRoutingMode?: string;
}

export interface SerializedElement {
  id: string;
  serviceType: ServiceType;
  name: string;
  position: Point;
  config: ResourceConfig;
}

export interface SerializedCanvasObject {
  id: string;
  objectType: CanvasObjectType;
  name: string;
  x?: number;
  y?: number;
  startX?: number;
  startY?: number;
  endX?: number;
  endY?: number;
  // Line anchors (v3)
  sourceAnchorObjectId?: string | null;
  targetAnchorObjectId?: string | null;
  // Line anchor positions (v3+)
  sourceAnchorPosition?: string | null;
  targetAnchorPosition?: string | null;
  // Line waypoints (user-modified intermediate points)
  waypoints?: { x: number; y: number }[];
  // Architecture block
  serviceType?: ServiceType;
  config?: ResourceConfig;
  terraformVariables?: Record<string, string | number | boolean>;
  // Text (v3)
  content?: string;
  // UML (v3)
  umlKind?: UMLKind;
  classData?: UMLClassData;
  // Visual
  visualConfig: Record<string, unknown>;
  zIndex?: number;
  groupId?: string;
}

export interface SerializedObjectGroup {
  id: string;
  name: string;
  memberIds: string[];
}

export interface SerializedConnector {
  id: string;
  sourceId: string;
  targetId: string;
  connectionType: string;
}

/** Maps to the backend's ArchitectureDescription Pydantic schema for Terraform export. */
export interface ArchitectureDescription {
  project_name: string;
  environments: { name: string; variables: Record<string, string> }[];
  resources: {
    name: string;
    service_type: string;
    config: ResourceConfig;
    terraform_variables?: Record<string, string | number | boolean>;
  }[];
  connections: {
    source: string;
    target: string;
    connection_type: string;
  }[];
  global_terraform_config?: {
    backend_type: string;
    backend_config: Record<string, string>;
    provider_region: string;
    provider_profile?: string;
    terraform_version?: string;
    aws_provider_version?: string;
  };
}
