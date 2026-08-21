import { describe, test, expect, beforeEach } from 'vitest';
import fc from 'fast-check';
import { computeShapeEdgePoint } from '@/utils/bounds-utils';
import { useDiagramStore } from '@/store/diagram-store';
import { DEFAULT_BLOCK_VISUAL } from '@/types/diagram';
import type { GeometricObject } from '@/types/diagram';

function circleAt(cx: number, cy: number, diameter: number): GeometricObject {
  return {
    id: 'circle-1',
    objectType: 'geometric',
    name: 'Circle',
    position: { x: cx, y: cy },
    visualConfig: {
      width: diameter,
      height: diameter,
      fill: false,
      fillColor: '#3b82f6',
      borderColor: '#ffffff',
      borderWidth: 2,
      shape: 'circle',
    },
    zIndex: 0,
  };
}

describe('computeShapeEdgePoint', () => {
  test('a line to a circle terminates on the perimeter, not the bounding box', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 40, max: 240 }),
        fc.integer({ min: -400, max: 400 }),
        fc.integer({ min: -400, max: 400 }),
        (diameter, dx, dy) => {
          fc.pre(dx !== 0 || dy !== 0);
          const cx = 200;
          const cy = 200;
          const radius = diameter / 2;
          const edge = computeShapeEdgePoint(circleAt(cx, cy, diameter), {
            x: cx + dx,
            y: cy + dy,
          });
          const dist = Math.hypot(edge.x - cx, edge.y - cy);
          expect(dist).toBeCloseTo(radius, 0);
        },
      ),
      { numRuns: 100 },
    );
  });
});

describe('addCanvasObject naming', () => {
  beforeEach(() => {
    useDiagramStore.setState({ canvasObjects: new Map(), _undoStack: [], _redoStack: [] });
  });

  function addBlock(name?: string): string {
    return useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'lambda',
      ...(name === undefined ? {} : { name }),
      position: { x: 100, y: 100 },
      config: {},
      terraformVariables: {},
      visualConfig: { ...DEFAULT_BLOCK_VISUAL },
    });
  }

  test('an explicitly provided name is preserved', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 30 }).filter((s) => s.trim().length > 0),
        (customName) => {
          useDiagramStore.setState({ canvasObjects: new Map(), _undoStack: [], _redoStack: [] });
          const id = addBlock(customName);
          expect(useDiagramStore.getState().canvasObjects.get(id)?.name).toBe(customName);
        },
      ),
      { numRuns: 50 },
    );
  });

  test('omitting the name generates a distinct default per object', () => {
    const names = [addBlock(), addBlock(), addBlock()].map(
      (id) => useDiagramStore.getState().canvasObjects.get(id)?.name,
    );
    expect(names.every((n) => typeof n === 'string' && n.length > 0)).toBe(true);
    expect(new Set(names).size).toBe(3);
  });
});
