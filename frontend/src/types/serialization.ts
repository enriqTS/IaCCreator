/**
 * Serialization types for save/load and backend API export.
 */

import type {
  CanvasObjectType,
  EnvironmentConfig,
  ResourceConfig,
  ServiceType,
  UMLClassData,
  UMLKind,
  Viewport,
} from './diagram';
import type { GlobalTerraformConfig } from './terraform-variables';

/** Current serialization format version. */
export const CURRENT_DIAGRAM_VERSION = 4;

/** Canonical diagram state exchanged with the backend. */
export interface DiagramState {
  version: number;
  projectName: string;
  environments: EnvironmentConfig[];
  canvasObjects?: SerializedCanvasObject[];
  connectors: SerializedConnector[];
  viewport: Viewport;
  objectGroups?: SerializedObjectGroup[];
  globalTerraformConfig?: GlobalTerraformConfig;
  globalRoutingMode?: string;
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
  parentContainerId?: string | null;
  presentation?: 'node' | 'container';
  containerType?: string;
  collapsed?: boolean;
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
  connection_config?: Record<string, string | number | boolean>;
  origin?: 'explicit' | 'containment';
  container_id?: string;
}
