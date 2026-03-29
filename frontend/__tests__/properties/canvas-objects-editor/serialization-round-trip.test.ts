import fc from 'fast-check';
import { describe, it, expect, beforeEach } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';
import type { CanvasObject, LineObject, GeometricObject, TextObject, UMLObject, ArchitectureBlock } from '@/types/diagram';
import {
  canvasObjectWithoutIdArbitrary,
  architectureBlockWithoutIdArbitrary,
  lineObjectWithoutIdArbitrary,
  geometricObjectWithoutIdArbitrary,
  textObjectWithoutIdArbitrary,
  umlObjectWithoutIdArbitrary,
  anchorRefArbitrary,
  pointArbitrary,
} from '../arbitraries';

/**
 * Feature: canvas-objects-editor, Property 12: Serialization round-trip for all object types
 * **Validates: Requirements 8.1, 8.2, 9.1, 9.2, 9.3, 9.4, 9.5**
 */
describe('Property 12: Serialization round-trip for all object types', () => {
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

  it('deserialize(serialize(objects)) ≡ objects for all 5 canvas object types', () => {
    fc.assert(
      fc.property(
        fc.array(canvasObjectWithoutIdArbitrary(), { minLength: 1, maxLength: 8 }),
        (payloads) => {
          const store = useDiagramStore.getState();

          // Add all objects to the store
          const ids: string[] = [];
          for (const payload of payloads) {
            const id = store.addCanvasObject(payload);
            ids.push(id);
          }

          // Capture the original objects
          const originalObjects = new Map<string, CanvasObject>();
          for (const id of ids) {
            const obj = useDiagramStore.getState().canvasObjects.get(id);
            if (obj) originalObjects.set(id, obj);
          }

          // Serialize
          const serialized = useDiagramStore.getState().serializeDiagramState();

          // Reset store
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

          // Deserialize
          useDiagramStore.getState().loadDiagramState(serialized);

          // Verify round-trip
          const loaded = useDiagramStore.getState().canvasObjects;
          expect(loaded.size).toBe(originalObjects.size);

          for (const [id, original] of originalObjects) {
            const restored = loaded.get(id);
            expect(restored).toBeDefined();
            expect(restored!.objectType).toBe(original.objectType);
            expect(restored!.name).toBe(original.name);
            expect(restored!.zIndex).toBe(original.zIndex);

            if (original.objectType === 'architecture-block') {
              const orig = original as ArchitectureBlock;
              const rest = restored as ArchitectureBlock;
              expect(rest.position).toEqual(orig.position);
              expect(rest.serviceType).toBe(orig.serviceType);
              expect(rest.config).toEqual(orig.config);
              expect(rest.visualConfig).toEqual(orig.visualConfig);
            } else if (original.objectType === 'line') {
              const orig = original as LineObject;
              const rest = restored as LineObject;
              expect(rest.start).toEqual(orig.start);
              expect(rest.end).toEqual(orig.end);
              expect(rest.sourceAnchor).toEqual(orig.sourceAnchor);
              expect(rest.targetAnchor).toEqual(orig.targetAnchor);
              expect(rest.visualConfig).toEqual(orig.visualConfig);
            } else if (original.objectType === 'geometric') {
              const orig = original as GeometricObject;
              const rest = restored as GeometricObject;
              expect(rest.position).toEqual(orig.position);
              expect(rest.visualConfig).toEqual(orig.visualConfig);
            } else if (original.objectType === 'text') {
              const orig = original as TextObject;
              const rest = restored as TextObject;
              expect(rest.position).toEqual(orig.position);
              expect(rest.content).toBe(orig.content);
              expect(rest.visualConfig).toEqual(orig.visualConfig);
            } else if (original.objectType === 'uml') {
              const orig = original as UMLObject;
              const rest = restored as UMLObject;
              expect(rest.position).toEqual(orig.position);
              expect(rest.umlKind).toBe(orig.umlKind);
              expect(rest.classData).toEqual(orig.classData);
              expect(rest.visualConfig).toEqual(orig.visualConfig);
            }
          }

          // Clean up for next iteration
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
        }
      ),
      { numRuns: 100 }
    );
  });

  it('round-trips lines with non-null anchors correctly', () => {
    fc.assert(
      fc.property(
        pointArbitrary(),
        pointArbitrary(),
        anchorRefArbitrary(),
        anchorRefArbitrary(),
        fc.string({ minLength: 1, maxLength: 20 }),
        (start, end, srcAnchor, tgtAnchor, name) => {
          const store = useDiagramStore.getState();

          const lineId = store.addCanvasObject({
            objectType: 'line',
            name,
            start,
            end,
            sourceAnchor: srcAnchor,
            targetAnchor: tgtAnchor,
            visualConfig: { color: '#ffffff', borderWidth: 2, strokeStyle: 'solid', startArrow: false, endArrow: false, routingMode: 'orthogonal' },
          });

          const original = useDiagramStore.getState().canvasObjects.get(lineId) as LineObject;

          const serialized = useDiagramStore.getState().serializeDiagramState();

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

          useDiagramStore.getState().loadDiagramState(serialized);

          const restored = useDiagramStore.getState().canvasObjects.get(lineId) as LineObject;
          expect(restored).toBeDefined();
          expect(restored.sourceAnchor).toEqual(original.sourceAnchor);
          expect(restored.targetAnchor).toEqual(original.targetAnchor);
          expect(restored.start).toEqual(original.start);
          expect(restored.end).toEqual(original.end);

          // Clean up
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
        }
      ),
      { numRuns: 100 }
    );
  });
});
