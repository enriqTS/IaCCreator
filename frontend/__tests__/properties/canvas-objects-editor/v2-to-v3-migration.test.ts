import fc from 'fast-check';
import { describe, it, expect, beforeEach } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';
import type { LineObject, ArchitectureBlock, GeometricObject } from '@/types/diagram';
import type { DiagramState, SerializedCanvasObject } from '@/types/serialization';
import {
  serviceTypeArbitrary,
  resourceConfigArbitrary,
  pointArbitrary,
  geometricShapeArbitrary,
  strokeStyleArbitrary,
} from '../arbitraries';
import { DEFAULT_LINE_VISUAL, DEFAULT_GEO_VISUAL, DEFAULT_BLOCK_VISUAL } from '@/types/diagram';
import { getDefaultVariables } from '@/types/terraform-variables';

/**
 * Feature: canvas-objects-editor, Property 13: v2 to v3 migration preserves existing objects
 * **Validates: Requirements 9.6**
 */
describe('Property 13: v2 to v3 migration preserves existing objects', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
      objectGroups: new Map(),
      connectors: new Map(),
      _undoStack: [],
      _redoStack: [],
      canUndo: false,
      canRedo: false,
    });
  });

  it('loading a v2 diagram state preserves all objects and adds null anchors to lines', () => {
    fc.assert(
      fc.property(
        // Generate a random v2 diagram state with architecture blocks, lines, and geometric objects
        fc.record({
          blocks: fc.array(
            fc.record({
              id: fc.uuid(),
              serviceType: serviceTypeArbitrary(),
              name: fc.string({ minLength: 1, maxLength: 20 }),
              x: fc.double({ min: -5000, max: 5000, noNaN: true, noDefaultInfinity: true }),
              y: fc.double({ min: -5000, max: 5000, noNaN: true, noDefaultInfinity: true }),
            }),
            { minLength: 0, maxLength: 4 }
          ),
          lines: fc.array(
            fc.record({
              id: fc.uuid(),
              name: fc.string({ minLength: 1, maxLength: 20 }),
              startX: fc.double({ min: -5000, max: 5000, noNaN: true, noDefaultInfinity: true }),
              startY: fc.double({ min: -5000, max: 5000, noNaN: true, noDefaultInfinity: true }),
              endX: fc.double({ min: -5000, max: 5000, noNaN: true, noDefaultInfinity: true }),
              endY: fc.double({ min: -5000, max: 5000, noNaN: true, noDefaultInfinity: true }),
            }),
            { minLength: 0, maxLength: 4 }
          ),
          geos: fc.array(
            fc.record({
              id: fc.uuid(),
              name: fc.string({ minLength: 1, maxLength: 20 }),
              x: fc.double({ min: -5000, max: 5000, noNaN: true, noDefaultInfinity: true }),
              y: fc.double({ min: -5000, max: 5000, noNaN: true, noDefaultInfinity: true }),
              shape: geometricShapeArbitrary(),
            }),
            { minLength: 0, maxLength: 4 }
          ),
        }),
        ({ blocks, lines, geos }) => {
          // Build a v2 DiagramState (no sourceAnchorObjectId/targetAnchorObjectId on lines)
          const canvasObjects: SerializedCanvasObject[] = [];
          let zIdx = 0;

          for (const b of blocks) {
            canvasObjects.push({
              id: b.id,
              objectType: 'architecture-block',
              name: b.name,
              x: b.x,
              y: b.y,
              serviceType: b.serviceType,
              config: {},
              terraformVariables: getDefaultVariables(b.serviceType),
              visualConfig: { ...DEFAULT_BLOCK_VISUAL } as Record<string, unknown>,
              zIndex: zIdx++,
            });
          }

          for (const l of lines) {
            canvasObjects.push({
              id: l.id,
              objectType: 'line',
              name: l.name,
              startX: l.startX,
              startY: l.startY,
              endX: l.endX,
              endY: l.endY,
              // v2: no sourceAnchorObjectId or targetAnchorObjectId
              visualConfig: { ...DEFAULT_LINE_VISUAL } as Record<string, unknown>,
              zIndex: zIdx++,
            });
          }

          for (const g of geos) {
            canvasObjects.push({
              id: g.id,
              objectType: 'geometric',
              name: g.name,
              x: g.x,
              y: g.y,
              visualConfig: { ...DEFAULT_GEO_VISUAL, shape: g.shape } as Record<string, unknown>,
              zIndex: zIdx++,
            });
          }

          const v2State: DiagramState = {
            version: 2,
            projectName: 'test-project',
            environments: [],
            elements: [],
            canvasObjects,
            connectors: [],
            viewport: { offsetX: 0, offsetY: 0, scale: 1 },
          };

          // Load the v2 state
          useDiagramStore.getState().loadDiagramState(v2State);

          const loaded = useDiagramStore.getState().canvasObjects;
          const totalExpected = blocks.length + lines.length + geos.length;

          // All objects preserved
          expect(loaded.size).toBe(totalExpected);

          // Verify architecture blocks preserved
          for (const b of blocks) {
            const obj = loaded.get(b.id) as ArchitectureBlock;
            expect(obj).toBeDefined();
            expect(obj.objectType).toBe('architecture-block');
            expect(obj.name).toBe(b.name);
            expect(obj.position.x).toBe(b.x);
            expect(obj.position.y).toBe(b.y);
            expect(obj.serviceType).toBe(b.serviceType);
          }

          // Verify lines gain sourceAnchor: null and targetAnchor: null
          for (const l of lines) {
            const obj = loaded.get(l.id) as LineObject;
            expect(obj).toBeDefined();
            expect(obj.objectType).toBe('line');
            expect(obj.name).toBe(l.name);
            expect(obj.start.x).toBe(l.startX);
            expect(obj.start.y).toBe(l.startY);
            expect(obj.end.x).toBe(l.endX);
            expect(obj.end.y).toBe(l.endY);
            expect(obj.sourceAnchor).toBeNull();
            expect(obj.targetAnchor).toBeNull();
          }

          // Verify geometric objects preserved with shape
          for (const g of geos) {
            const obj = loaded.get(g.id) as GeometricObject;
            expect(obj).toBeDefined();
            expect(obj.objectType).toBe('geometric');
            expect(obj.name).toBe(g.name);
            expect(obj.position.x).toBe(g.x);
            expect(obj.position.y).toBe(g.y);
            expect(obj.visualConfig.shape).toBe(g.shape);
          }

          // Clean up for next iteration
          useDiagramStore.setState({
            canvasObjects: new Map(),
            selectedObjectIds: new Set(),
            objectGroups: new Map(),
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
