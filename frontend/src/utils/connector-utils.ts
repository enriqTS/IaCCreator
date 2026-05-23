/**
 * Connector utility functions for associating LineObjects with Connectors
 * and resolving connection schemas.
 *
 * A line is associated with a connector when:
 * 1. The line's sourceAnchor.objectId references an architecture block
 * 2. The line's targetAnchor.objectId references an architecture block
 * 3. A connector exists with sourceId matching the source block and targetId matching the target block
 */

import type { LineObject, Connector, CanvasObject, ArchitectureBlock } from '@/types/diagram';
import {
  CONNECTION_SCHEMA_REGISTRY,
  type ConnectionSchema,
  type SchemaRegistryKey,
} from '@/config/connection-schemas';
import { v4 as uuidv4 } from 'uuid';

/**
 * Finds the Connector associated with a LineObject by matching the line's
 * source and target anchors to architecture blocks referenced by a connector.
 *
 * Returns null if:
 * - The line has no sourceAnchor or targetAnchor
 * - The anchored objects are not architecture blocks
 * - No connector matches the source/target block pair
 */
export function findConnectorForLine(
  line: LineObject,
  connectors: Map<string, Connector>,
  canvasObjects: Map<string, CanvasObject>,
): Connector | null {
  // Line must have both anchors set
  if (!line.sourceAnchor || !line.targetAnchor) {
    return null;
  }

  const sourceObjectId = line.sourceAnchor.objectId;
  const targetObjectId = line.targetAnchor.objectId;

  // Both anchored objects must be architecture blocks
  const sourceObj = canvasObjects.get(sourceObjectId);
  const targetObj = canvasObjects.get(targetObjectId);

  if (!sourceObj || sourceObj.objectType !== 'architecture-block') {
    return null;
  }
  if (!targetObj || targetObj.objectType !== 'architecture-block') {
    return null;
  }

  // Find a connector that matches this source/target pair (check both directions)
  for (const connector of connectors.values()) {
    if (
      (connector.sourceId === sourceObjectId && connector.targetId === targetObjectId) ||
      (connector.sourceId === targetObjectId && connector.targetId === sourceObjectId)
    ) {
      return connector;
    }
  }

  return null;
}

/**
 * Resolves the ConnectionSchema from the registry based on the source and target
 * service types of the connected architecture blocks.
 *
 * Returns null if:
 * - The source or target block cannot be found in canvasObjects
 * - The service pair has no entry in the schema registry
 */
export function getSchemaForConnector(
  connector: Connector,
  canvasObjects: Map<string, CanvasObject>,
): ConnectionSchema | null {
  const sourceObj = canvasObjects.get(connector.sourceId);
  const targetObj = canvasObjects.get(connector.targetId);

  if (!sourceObj || sourceObj.objectType !== 'architecture-block') {
    return null;
  }
  if (!targetObj || targetObj.objectType !== 'architecture-block') {
    return null;
  }

  const key: SchemaRegistryKey =
    `${sourceObj.serviceType}::${targetObj.serviceType}` as SchemaRegistryKey;

  // Try the direct key first, then the reverse direction
  const schema = CONNECTION_SCHEMA_REGISTRY.get(key);
  if (schema) return schema;

  const reverseKey: SchemaRegistryKey =
    `${targetObj.serviceType}::${sourceObj.serviceType}` as SchemaRegistryKey;
  return CONNECTION_SCHEMA_REGISTRY.get(reverseKey) ?? null;
}

/**
 * Finds an existing connector for the line, or creates a new one if the line
 * connects two architecture blocks and no connector exists yet.
 *
 * Returns null if the line does not connect two architecture blocks.
 *
 * Note: This function creates the connector object but does NOT add it to the store.
 * The caller is responsible for persisting the returned connector if it is newly created.
 * Check `connector.id` against the connectors map to determine if it's new.
 */
export function ensureConnectorForLine(
  line: LineObject,
  canvasObjects: Map<string, CanvasObject>,
  connectors: Map<string, Connector>,
): Connector | null {
  // Line must have both anchors set
  if (!line.sourceAnchor || !line.targetAnchor) {
    return null;
  }

  const sourceObjectId = line.sourceAnchor.objectId;
  const targetObjectId = line.targetAnchor.objectId;

  // Both anchored objects must be architecture blocks
  const sourceObj = canvasObjects.get(sourceObjectId);
  const targetObj = canvasObjects.get(targetObjectId);

  if (!sourceObj || sourceObj.objectType !== 'architecture-block') {
    return null;
  }
  if (!targetObj || targetObj.objectType !== 'architecture-block') {
    return null;
  }

  // Try to find an existing connector for this pair
  const existing = findConnectorForLine(line, connectors, canvasObjects);
  if (existing) {
    return existing;
  }

  // Create a new connector
  const newConnector: Connector = {
    id: uuidv4(),
    sourceId: sourceObjectId,
    targetId: targetObjectId,
    connectionType: 'triggers',
  };

  return newConnector;
}
