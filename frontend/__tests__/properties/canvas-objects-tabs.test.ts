import fc from 'fast-check';
import { getTabsForObject } from '@/components/config/BottomPanel';
import type { CanvasObject, CanvasObjectCreationPayload } from '@/types/diagram';
import {
  canvasObjectWithoutIdArbitrary,
  architectureBlockWithoutIdArbitrary,
  lineObjectWithoutIdArbitrary,
  geometricObjectWithoutIdArbitrary,
} from './arbitraries';

/**
 * Helper: attach a random UUID-style id to a canvas object without id.
 */
function withId(obj: CanvasObjectCreationPayload): CanvasObject {
  return { ...obj, id: crypto.randomUUID(), zIndex: 0 } as CanvasObject;
}

// Feature: canvas-objects-editor, Property 7: Tab configuration matches object type
// **Validates: Requirements 5.1, 5.2**
describe('Property 7: Tab configuration matches object type', () => {
  test('architecture blocks get Terraform, Variables, and Visual tabs', () => {
    fc.assert(
      fc.property(
        architectureBlockWithoutIdArbitrary(),
        (objWithoutId) => {
          const obj = withId(objWithoutId);
          const tabs = getTabsForObject(obj);

          expect(tabs).toEqual(['Terraform', 'Variables', 'Visual']);
        }
      ),
      { numRuns: 100 }
    );
  });

  test('line objects get only the Visual tab', () => {
    fc.assert(
      fc.property(
        lineObjectWithoutIdArbitrary(),
        (objWithoutId) => {
          const obj = withId(objWithoutId);
          const tabs = getTabsForObject(obj);

          expect(tabs).toEqual(['Visual']);
        }
      ),
      { numRuns: 100 }
    );
  });

  test('geometric objects get only the Visual tab', () => {
    fc.assert(
      fc.property(
        geometricObjectWithoutIdArbitrary(),
        (objWithoutId) => {
          const obj = withId(objWithoutId);
          const tabs = getTabsForObject(obj);

          expect(tabs).toEqual(['Visual']);
        }
      ),
      { numRuns: 100 }
    );
  });

  test('for any canvas object: architecture blocks get 3 tabs, others get 1', () => {
    fc.assert(
      fc.property(
        canvasObjectWithoutIdArbitrary(),
        (objWithoutId) => {
          const obj = withId(objWithoutId);
          const tabs = getTabsForObject(obj);

          if (obj.objectType === 'architecture-block') {
            expect(tabs).toHaveLength(3);
            expect(tabs).toContain('Terraform');
            expect(tabs).toContain('Variables');
            expect(tabs).toContain('Visual');
          } else {
            expect(tabs).toHaveLength(1);
            expect(tabs).toEqual(['Visual']);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
