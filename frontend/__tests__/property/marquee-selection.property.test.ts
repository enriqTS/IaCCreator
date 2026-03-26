/**
 * Property-based test: Marquee selection correctness
 *
 * **Validates: Requirements 7.2, 7.3**
 *
 * Property 8: selectObjectsByRect adds exactly those objects whose bounding boxes
 * intersect the given rectangle.
 */
import { describe, it, beforeEach } from 'vitest';
import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { getObjectBounds } from '@/types/diagram';
import type { Rect } from '@/types/diagram';
import { canvasObjectWithoutIdArbitrary } from '../properties/arbitraries';

/**
 * AABB intersection check: returns true if rectangles a and b overlap.
 */
function rectsIntersect(a: Rect, b: Rect): boolean {
  return (
    a.x < b.x + b.width &&
    a.x + a.width > b.x &&
    a.y < b.y + b.height &&
    a.y + a.height > b.y
  );
}

/**
 * Arbitrary that generates a marquee rectangle with positive width/height.
 */
const marqueeRectArbitrary: fc.Arbitrary<Rect> = fc.record({
  x: fc.double({ min: -5000, max: 5000, noNaN: true, noDefaultInfinity: true }),
  y: fc.double({ min: -5000, max: 5000, noNaN: true, noDefaultInfinity: true }),
  width: fc.double({ min: 1, max: 2000, noNaN: true, noDefaultInfinity: true }),
  height: fc.double({ min: 1, max: 2000, noNaN: true, noDefaultInfinity: true }),
});

describe('Marquee Selection Correctness Property', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
      objectGroups: new Map(),
    });
  });

  it('Property 8: selectObjectsByRect adds exactly those objects whose bounding boxes intersect the given rectangle', () => {
    /**
     * **Validates: Requirements 7.2, 7.3**
     *
     * Strategy:
     * 1. Generate a random set of canvas objects with various positions and sizes
     * 2. Generate a random marquee rectangle
     * 3. Call selectObjectsByRect(rect) on the store
     * 4. Independently compute which objects should be selected by checking AABB
     *    intersection of each object's bounding box with the marquee rect
     * 5. Verify that selectedObjectIds matches exactly the expected set
     */
    fc.assert(
      fc.property(
        fc.array(canvasObjectWithoutIdArbitrary(), { minLength: 1, maxLength: 15 }),
        marqueeRectArbitrary,
        (objectPayloads, marqueeRect) => {
          const store = useDiagramStore.getState();

          // Add all objects to the store
          const addedIds: string[] = [];
          for (const payload of objectPayloads) {
            const id = store.addCanvasObject(payload);
            addedIds.push(id);
          }

          // Call selectObjectsByRect
          useDiagramStore.getState().selectObjectsByRect(marqueeRect);

          // Independently compute expected selection
          const { canvasObjects, selectedObjectIds } = useDiagramStore.getState();
          const expectedIds = new Set<string>();
          for (const obj of canvasObjects.values()) {
            const bounds = getObjectBounds(obj);
            if (rectsIntersect(bounds, marqueeRect)) {
              expectedIds.add(obj.id);
            }
          }

          // Verify exact match
          if (selectedObjectIds.size !== expectedIds.size) return false;
          for (const id of expectedIds) {
            if (!selectedObjectIds.has(id)) return false;
          }
          return true;
        },
      ),
      { numRuns: 200 },
    );
  });
});
