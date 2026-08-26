/**
 * Connector utility functions for associating LineObjects with Connectors
 * and resolving connection schemas.
 *
 * A line is associated with a connector when:
 * 1. The line's sourceAnchor.objectId references an architecture block
 * 2. The line's targetAnchor.objectId references an architecture block
 * 3. A connector exists with sourceId matching the source block and targetId matching the target block
 */

import type { LineObject, Connector, CanvasObject } from '@/types/diagram';
import type { ConnectionSchema } from './registry';
import { getConnectionSchema } from './schema-store';

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
 * - The service pair is not in the backend catalog (or it has not loaded yet)
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

  // Try the drawn direction first, then the reverse, since a line has no inherent direction
  return (
    getConnectionSchema(
      sourceObj.serviceType,
      targetObj.serviceType,
      connector.connectionType,
    ) ??
    getConnectionSchema(
      targetObj.serviceType,
      sourceObj.serviceType,
      connector.connectionType,
    )
  );
}
