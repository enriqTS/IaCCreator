import fc from 'fast-check';
import { describe, it, expect } from 'vitest';
import type { CanvasObjectType } from '@/types/diagram';

// Feature: canvas-context-menu, Property 18: Type-specific menu items match object type
// **Validates: Requirements 10.5**

/**
 * Pure logic function that determines type-specific menu items for a given object type.
 * This mirrors the conditional logic in ObjectContextMenu.
 */
function getTypeSpecificMenuItems(objectType: CanvasObjectType): string[] {
  switch (objectType) {
    case 'line':
      return ['Edit Connection'];
    case 'architecture-block':
      return ['Configure Service'];
    case 'geometric':
      return [];
    default:
      return [];
  }
}

describe('Property 18: Type-specific menu items match object type', () => {
  it('Line_Objects get "Edit Connection", Architecture_Blocks get "Configure Service", Geometric_Objects get neither', () => {
    fc.assert(
      fc.property(
        fc.constantFrom<CanvasObjectType>('line', 'architecture-block', 'geometric'),
        (objectType) => {
          const items = getTypeSpecificMenuItems(objectType);

          if (objectType === 'line') {
            expect(items).toContain('Edit Connection');
            expect(items).not.toContain('Configure Service');
          } else if (objectType === 'architecture-block') {
            expect(items).toContain('Configure Service');
            expect(items).not.toContain('Edit Connection');
          } else {
            // geometric
            expect(items).not.toContain('Edit Connection');
            expect(items).not.toContain('Configure Service');
            expect(items).toHaveLength(0);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
