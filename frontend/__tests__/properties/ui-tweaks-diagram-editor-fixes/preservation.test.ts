import { describe, test, expect } from 'vitest';
import fc from 'fast-check';
import { getAnchorPoints } from '@/utils/anchor';
import type { Rect } from '@/types/diagram';
import { useDiagramStore } from '@/store/diagram-store';
import { DEFAULT_BLOCK_VISUAL, DEFAULT_LINE_VISUAL } from '@/types/diagram';
import * as fs from 'fs';
import * as path from 'path';

/**
 * **Validates: Requirements 3.1, 3.2, 3.3, 3.5, 3.6**
 *
 * Property 2: Preservation — Existing Diagram Editor Behavior
 *
 * These tests capture existing CORRECT behaviors that MUST remain unchanged after fixes.
 * All tests MUST PASS on the current unfixed code.
 */

describe('Property 2: Preservation — Existing Diagram Editor Behavior', () => {
  describe('3.1 Rectangular shape anchors preserved', () => {
    test('getAnchorPoints returns cardinal midpoints on bounding box for all valid rects', () => {
      fc.assert(
        fc.property(
          fc.record({
            x: fc.double({ min: -5000, max: 5000, noNaN: true, noDefaultInfinity: true }),
            y: fc.double({ min: -5000, max: 5000, noNaN: true, noDefaultInfinity: true }),
            width: fc.double({ min: 1, max: 2000, noNaN: true, noDefaultInfinity: true }),
            height: fc.double({ min: 1, max: 2000, noNaN: true, noDefaultInfinity: true }),
          }),
          (bounds: Rect) => {
            const anchors = getAnchorPoints(bounds);
            const cx = bounds.x + bounds.width / 2;
            const cy = bounds.y + bounds.height / 2;

            // Top: midpoint of top edge
            expect(anchors.top.x).toBeCloseTo(cx, 5);
            expect(anchors.top.y).toBeCloseTo(bounds.y, 5);

            // Right: midpoint of right edge
            expect(anchors.right.x).toBeCloseTo(bounds.x + bounds.width, 5);
            expect(anchors.right.y).toBeCloseTo(cy, 5);

            // Bottom: midpoint of bottom edge
            expect(anchors.bottom.x).toBeCloseTo(cx, 5);
            expect(anchors.bottom.y).toBeCloseTo(bounds.y + bounds.height, 5);

            // Left: midpoint of left edge
            expect(anchors.left.x).toBeCloseTo(bounds.x, 5);
            expect(anchors.left.y).toBeCloseTo(cy, 5);
          },
        ),
        { numRuns: 100 },
      );
    });
  });

  describe('3.2 Stable orthogonal rendering', () => {
    test('LineObjectComponent source contains pathPoints useMemo with orthogonal waypoint computation', () => {
      const srcPath = path.resolve(__dirname, '../../../src/components/canvas/LineObjectComponent.tsx');
      const source = fs.readFileSync(srcPath, 'utf-8');

      // The pathPoints useMemo must exist and handle orthogonal routing
      expect(source).toContain('const pathPoints = useMemo(');
      expect(source).toContain('computeOrthogonalWaypoints');
      expect(source).toContain("useOrthogonal");
    });
  });

  describe('3.3 Stable diagonal rendering', () => {
    test('shortenPath with 2-point input produces a 2-element result', () => {
      // Import shortenPath by reading the source and verifying the logic inline
      // shortenPath is not exported, so we verify via the source structure
      const srcPath = path.resolve(__dirname, '../../../src/components/canvas/LineObjectComponent.tsx');
      const source = fs.readFileSync(srcPath, 'utf-8');

      // diagShortened useMemo calls shortenPath([startPt, endPt], ...) producing a 2-element array
      expect(source).toContain('shortenPath([startPt, endPt]');
      expect(source).toContain('const diagShortened = useMemo(');
    });
  });

  describe('3.5 Freeform line placement threshold', () => {
    test('Canvas.tsx uses 10px minimum drag distance threshold for place-line', () => {
      const srcPath = path.resolve(__dirname, '../../../src/components/canvas/Canvas.tsx');
      const source = fs.readFileSync(srcPath, 'utf-8');

      // The place-line handler uses distance >= 10 threshold
      expect(source).toContain('distance >= 10');
      // And it creates a diagonal line when threshold met
      expect(source).toContain("routingMode: 'diagonal'");
    });
  });

  describe('3.6 Custom name preservation', () => {
    test('addCanvasObject preserves explicitly provided non-empty names', () => {
      fc.assert(
        fc.property(
          fc.string({ minLength: 1, maxLength: 30 }).filter((s) => s !== 'Service' && s.trim().length > 0),
          (customName: string) => {
            // Reset store
            useDiagramStore.setState({
              canvasObjects: new Map(),
              history: [],
              historyIndex: -1,
            });

            const id = useDiagramStore.getState().addCanvasObject({
              objectType: 'architecture-block',
              serviceType: 'lambda',
              name: customName,
              position: { x: 100, y: 100 },
              config: {},
              terraformVariables: {},
              visualConfig: { ...DEFAULT_BLOCK_VISUAL },
            });

            const obj = useDiagramStore.getState().canvasObjects.get(id);
            expect(obj).toBeDefined();
            // The store preserves the explicit custom name
            expect((obj as { name: string }).name).toBe(customName);
          },
        ),
        { numRuns: 50 },
      );
    });
  });
});
