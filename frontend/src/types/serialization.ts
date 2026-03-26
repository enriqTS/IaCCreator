/**
 * Serialization types for save/load and backend API export.
 */

import type {
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
