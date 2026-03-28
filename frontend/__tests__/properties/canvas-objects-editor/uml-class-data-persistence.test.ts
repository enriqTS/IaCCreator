import fc from 'fast-check';
import { describe, it, expect, beforeEach } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';
import type { UMLObject, UMLKind } from '@/types/diagram';
import { DEFAULT_UML_VISUAL, DEFAULT_UML_CLASS_DATA } from '@/types/diagram';

/**
 * Feature: canvas-objects-editor, Property 11: UML class data persistence
 * **Validates: Requirements 6.9**
 */
describe('Property 11: UML class data persistence', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
      objectGroups: new Map(),
      elements: new Map(),
      connectors: new Map(),
      _undoStack: [],
      _redoStack: [],
      canUndo: false,
      canRedo: false,
    });
  });

  it('adding attributes and methods to a class/interface UML object persists them through the store', () => {
    fc.assert(
      fc.property(
        fc.record({
          umlKind: fc.constantFrom('class', 'interface') as fc.Arbitrary<UMLKind>,
          attributes: fc.array(fc.string({ minLength: 1, maxLength: 50 }).filter((s) => s.trim().length > 0), { minLength: 0, maxLength: 10 }),
          methods: fc.array(fc.string({ minLength: 1, maxLength: 50 }).filter((s) => s.trim().length > 0), { minLength: 0, maxLength: 10 }),
          posX: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
          posY: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
        }),
        ({ umlKind, attributes, methods, posX, posY }) => {
          const store = useDiagramStore.getState();

          // Create a UML object with classData
          const umlId = store.addCanvasObject({
            objectType: 'uml',
            name: 'TestUML',
            position: { x: posX, y: posY },
            umlKind,
            classData: { ...DEFAULT_UML_CLASS_DATA },
            visualConfig: { ...DEFAULT_UML_VISUAL },
          });

          // Verify it was created
          const created = useDiagramStore.getState().canvasObjects.get(umlId) as UMLObject;
          expect(created).toBeDefined();
          expect(created.objectType).toBe('uml');
          expect(created.umlKind).toBe(umlKind);
          expect(created.classData).toBeDefined();

          // Update with attributes and methods
          useDiagramStore.getState().updateCanvasObject(umlId, {
            classData: { attributes, methods },
          } as Partial<UMLObject>);

          // Read back and verify
          const updated = useDiagramStore.getState().canvasObjects.get(umlId) as UMLObject;
          expect(updated).toBeDefined();
          expect(updated.classData).toBeDefined();
          expect(updated.classData!.attributes).toEqual(attributes);
          expect(updated.classData!.methods).toEqual(methods);

          // Clean up for next iteration
          useDiagramStore.setState({
            canvasObjects: new Map(),
            selectedObjectIds: new Set(),
            objectGroups: new Map(),
            _undoStack: [],
            _redoStack: [],
            canUndo: false,
            canRedo: false,
          });
        }
      ),
      { numRuns: 100 }
    );
  });
});
