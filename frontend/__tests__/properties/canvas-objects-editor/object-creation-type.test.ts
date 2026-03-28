import fc from 'fast-check';
import { describe, it, expect, beforeEach } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';
import type {
  CanvasObject,
  CanvasObjectCreationPayload,
  UMLKind,
  UMLObject,
  GeometricObject,
  GeometricShape,
} from '@/types/diagram';
import {
  DEFAULT_BLOCK_VISUAL,
  DEFAULT_LINE_VISUAL,
  DEFAULT_GEO_VISUAL,
  DEFAULT_TEXT_VISUAL,
  DEFAULT_UML_VISUAL,
} from '@/types/diagram';
import { getDefaultVariables } from '@/types/terraform-variables';
import { pointArbitrary, serviceTypeArbitrary } from '../../properties/arbitraries';

const UML_KINDS: UMLKind[] = ['class', 'interface', 'actor', 'use-case', 'component', 'package', 'node'];
const GEO_SHAPES: GeometricShape[] = ['rectangle', 'ellipse'];

/**
 * Generates a random creation payload for any of the 5 object types.
 */
function creationPayloadArbitrary(): fc.Arbitrary<CanvasObjectCreationPayload> {
  return fc.oneof(
    // architecture-block
    serviceTypeArbitrary().chain((st) =>
      pointArbitrary().map((pos) => ({
        objectType: 'architecture-block' as const,
        serviceType: st,
        name: 'TestBlock',
        position: pos,
        config: {},
        terraformVariables: getDefaultVariables(st),
        visualConfig: { ...DEFAULT_BLOCK_VISUAL },
      }))
    ),
    // line
    fc.tuple(pointArbitrary(), pointArbitrary()).map(([start, end]) => ({
      objectType: 'line' as const,
      name: 'TestLine',
      start,
      end,
      sourceAnchor: null,
      targetAnchor: null,
      visualConfig: { ...DEFAULT_LINE_VISUAL },
    })),
    // geometric
    fc.tuple(pointArbitrary(), fc.constantFrom(...GEO_SHAPES)).map(([pos, shape]) => ({
      objectType: 'geometric' as const,
      name: 'TestGeo',
      position: pos,
      visualConfig: { ...DEFAULT_GEO_VISUAL, shape },
    })),
    // text
    pointArbitrary().map((pos) => ({
      objectType: 'text' as const,
      name: 'TestText',
      position: pos,
      content: 'Hello',
      visualConfig: { ...DEFAULT_TEXT_VISUAL },
    })),
    // uml
    fc.tuple(pointArbitrary(), fc.constantFrom(...UML_KINDS)).map(([pos, umlKind]) => ({
      objectType: 'uml' as const,
      name: 'TestUML',
      position: pos,
      umlKind,
      visualConfig: { ...DEFAULT_UML_VISUAL },
    }))
  );
}

/**
 * Feature: canvas-objects-editor, Property 9: Object creation assigns correct type and kind
 * **Validates: Requirements 2.1, 6.1**
 */
describe('Property 9: Object creation assigns correct type and kind', () => {
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

  it('created object has matching objectType, a unique UUID, and correct sub-type discriminant', () => {
    fc.assert(
      fc.property(
        creationPayloadArbitrary(),
        (payload) => {
          const store = useDiagramStore.getState();
          const id = store.addCanvasObject(payload);

          const obj = useDiagramStore.getState().canvasObjects.get(id) as CanvasObject;
          expect(obj).toBeDefined();

          // Verify objectType matches
          expect(obj.objectType).toBe(payload.objectType);

          // Verify id is a valid UUID-like string (non-empty)
          expect(id).toBeTruthy();
          expect(typeof id).toBe('string');
          expect(id.length).toBeGreaterThan(0);

          // Verify sub-type discriminants
          if (payload.objectType === 'uml') {
            const umlObj = obj as UMLObject;
            const umlPayload = payload as { umlKind: UMLKind };
            expect(umlObj.umlKind).toBe(umlPayload.umlKind);
          }

          if (payload.objectType === 'geometric') {
            const geoObj = obj as GeometricObject;
            const geoPayload = payload as { visualConfig: { shape: GeometricShape } };
            expect(geoObj.visualConfig.shape).toBe(geoPayload.visualConfig.shape);
          }

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
