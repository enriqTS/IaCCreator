/**
 * Utility functions for generating default names for Architecture Blocks.
 *
 * Default names follow the pattern "{serviceType}-{N}" where N is an
 * incrementing integer starting at 1 for each service type.
 */

import type { ServiceType, CanvasObject } from '@/types/diagram';

/**
 * Extract the counter value from a default name pattern "{serviceType}-{N}".
 * Returns NaN if the name doesn't match the expected pattern.
 */
function parseCounter(name: string, serviceType: ServiceType): number {
  const prefix = `${serviceType}-`;
  if (!name.startsWith(prefix)) {
    return NaN;
  }
  const suffix = name.slice(prefix.length);
  // Must be a pure integer (no extra characters)
  if (!/^\d+$/.test(suffix)) {
    return NaN;
  }
  return parseInt(suffix, 10);
}

/**
 * Generate a unique default name for a new Architecture Block.
 *
 * Pattern: "{serviceType}-{N}" where N is 1 + max existing counter for that type.
 * Scans all existing architecture-block objects and finds the highest counter
 * for the given serviceType.
 *
 * Edge cases:
 * - Empty canvas (no existing objects) → returns "{serviceType}-1"
 * - Non-pattern names (manually renamed blocks) are ignored in counter calculation
 * - NaN values from malformed names are ignored
 */
export function generateDefaultName(
  serviceType: ServiceType,
  existingObjects: Map<string, CanvasObject>,
): string {
  let maxCounter = 0;

  for (const obj of existingObjects.values()) {
    if (obj.objectType !== 'architecture-block') {
      continue;
    }
    if (obj.serviceType !== serviceType) {
      continue;
    }
    const counter = parseCounter(obj.name, serviceType);
    if (!isNaN(counter) && counter > maxCounter) {
      maxCounter = counter;
    }
  }

  return `${serviceType}-${maxCounter + 1}`;
}
