import fc from 'fast-check';
import { describe, it, expect } from 'vitest';
import { SHAPE_PATH_REGISTRY } from '@/utils/shape-paths';
import type { GeometricShape } from '@/types/diagram';

/**
 * All 26 geometric shape variants.
 */
const ALL_SHAPES: GeometricShape[] = [
  'rectangle', 'rounded-rectangle', 'ellipse', 'circle',
  'triangle', 'diamond', 'parallelogram', 'trapezoid',
  'hexagon', 'octagon', 'pentagon', 'star', 'cross',
  'arrow-right', 'arrow-left', 'arrow-up', 'arrow-down',
  'chevron', 'cylinder', 'cloud', 'callout',
  'document', 'process', 'decision', 'data', 'predefined-process',
];

/**
 * Arbitrary for a geometric shape variant.
 */
function shapeArbitrary(): fc.Arbitrary<GeometricShape> {
  return fc.constantFrom(...ALL_SHAPES);
}

/**
 * Arbitrary for valid dimensions (width >= 40, height >= 40).
 */
function dimensionsArbitrary(): fc.Arbitrary<{ width: number; height: number }> {
  return fc.record({
    width: fc.double({ min: 40, max: 2000, noNaN: true, noDefaultInfinity: true }),
    height: fc.double({ min: 40, max: 2000, noNaN: true, noDefaultInfinity: true }),
  });
}

/**
 * Extract coordinate pairs from M (moveto) and L (lineto) commands in an SVG path.
 * These commands use simple x,y coordinate pairs.
 * Returns array of { x, y } objects.
 */
function extractMLCoordinates(path: string): { x: number; y: number }[] {
  const coords: { x: number; y: number }[] = [];
  const numberPattern = /-?\d+(?:\.\d+)?(?:e[+-]?\d+)?/g;

  // Split path into segments by SVG command letters
  // We only care about M and L commands for coordinate bounds checking
  const segments = path.split(/(?=[MLHVCSQTAZ])/i);

  for (const segment of segments) {
    const trimmed = segment.trim();
    if (!trimmed) continue;

    const cmd = trimmed[0].toUpperCase();
    if (cmd !== 'M' && cmd !== 'L') continue;

    // Extract all numbers from this M/L segment
    const rest = trimmed.slice(1);
    const numbers: number[] = [];
    let match: RegExpExecArray | null;
    numberPattern.lastIndex = 0;
    while ((match = numberPattern.exec(rest)) !== null) {
      numbers.push(Number(match[0]));
    }

    // M and L commands have pairs of (x, y) coordinates
    for (let i = 0; i + 1 < numbers.length; i += 2) {
      coords.push({ x: numbers[i], y: numbers[i + 1] });
    }
  }

  return coords;
}

const TOLERANCE = 0.01;

// Feature: canvas-objects-editor, Property 8: Shape path validity and bounds containment
// **Validates: Requirements 5.3, 5.4**
describe('Property 8: Shape path validity and bounds containment', () => {
  it('every shape path function returns a non-empty string for valid dimensions', () => {
    fc.assert(
      fc.property(
        shapeArbitrary(),
        dimensionsArbitrary(),
        (shape, { width, height }) => {
          const pathFn = SHAPE_PATH_REGISTRY[shape];
          expect(pathFn).toBeDefined();

          const pathStr = pathFn(width, height);
          expect(typeof pathStr).toBe('string');
          expect(pathStr.length).toBeGreaterThan(0);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('all M/L coordinates in the path are within bounds [0, width] x [0, height] with tolerance', () => {
    fc.assert(
      fc.property(
        shapeArbitrary(),
        dimensionsArbitrary(),
        (shape, { width, height }) => {
          const pathFn = SHAPE_PATH_REGISTRY[shape];
          const pathStr = pathFn(width, height);

          const coords = extractMLCoordinates(pathStr);

          // M/L commands should produce at least some coordinate pairs
          expect(coords.length).toBeGreaterThan(0);

          for (const { x, y } of coords) {
            // x-coordinates within [-tolerance, width+tolerance]
            expect(x).toBeGreaterThanOrEqual(-TOLERANCE);
            expect(x).toBeLessThanOrEqual(width + TOLERANCE);
            // y-coordinates within [-tolerance, height+tolerance]
            expect(y).toBeGreaterThanOrEqual(-TOLERANCE);
            expect(y).toBeLessThanOrEqual(height + TOLERANCE);
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it('all 26 shape variants are present in the registry', () => {
    for (const shape of ALL_SHAPES) {
      expect(SHAPE_PATH_REGISTRY[shape]).toBeDefined();
      expect(typeof SHAPE_PATH_REGISTRY[shape]).toBe('function');
    }
  });
});
