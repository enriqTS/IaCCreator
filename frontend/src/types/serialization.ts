/**
 * Serialization types for save/load and backend API export.
 */

import type {
  CanvasObjectType,
  EnvironmentConfig,
  Point,
  ResourceConfig,
  ServiceType,
  Viewport,
} from './diagram';

/** Full diagram state for save/load to localStorage. */
export interface DiagramState {
  version: number;
  projectName: string;
  environments: EnvironmentConfig[];
  elements: SerializedElement[];
  canvasObjects?: SerializedCanvasObject[];
  connectors: SerializedConnector[];
  viewport: Viewport;
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
  serviceType?: ServiceType;
  config?: ResourceConfig;
  visualConfig: Record<string, unknown>;
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
  }[];
  connections: {
    source: string;
    target: string;
    connection_type: string;
  }[];
}
