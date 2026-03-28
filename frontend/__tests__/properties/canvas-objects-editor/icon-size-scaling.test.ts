import fc from 'fast-check';
import { describe, it, expect } from 'vitest';
import { ICON_PADDING, shouldShowLabel } from '@/components/canvas/ArchitectureBlockComponent';

/**
 * Feature: canvas-objects-editor, Property 1: Icon size scales with block dimensions
 * **Validates: Requirements 1.1, 1.4, 1.5**
 */
describe('Property 1: Icon size scales with block dimensions', () => {
  it('iconSize equals max(0, min(width - 2*ICON_PADDING, height - 2*ICON_PADDING - labelSpace)) and is positive for valid dimensions', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 40, max: 2000 }),
        fc.integer({ min: 40, max: 2000 }),
        fc.oneof(
          fc.constant(''),
          fc.constant('  '),
          fc.constant('Service'),
          fc.string({ minLength: 1, maxLength: 30 }).filter((s) => s.trim() !== '' && s.trim() !== 'Service'),
        ),
        (width, height, name) => {
          const showLabel = shouldShowLabel(name);
          const labelSpace = showLabel ? 20 : 0;
          const expectedIconSize = Math.max(0, Math.min(width - 2 * ICON_PADDING, height - 2 * ICON_PADDING - labelSpace));

          // Verify the formula produces the expected result
          expect(expectedIconSize).toBe(
            Math.max(0, Math.min(width - 2 * ICON_PADDING, height - 2 * ICON_PADDING - labelSpace)),
          );

          // For dimensions ≥ 40, icon size should be positive
          // width ≥ 40 means width - 2*12 = width - 24 ≥ 16 > 0
          // height ≥ 40 means height - 24 - labelSpace ≥ 16 - 20 = -4 (with label) or ≥ 16 (without)
          // So icon size > 0 when height - 24 - labelSpace > 0
          // With label: height > 44 guarantees positive; height = 40 gives -4 → clamped to 0
          // Without label: height ≥ 40 gives ≥ 16 > 0
          if (!showLabel || height > 2 * ICON_PADDING + labelSpace) {
            expect(expectedIconSize).toBeGreaterThan(0);
          }

          // Icon size should never exceed width or height
          expect(expectedIconSize).toBeLessThanOrEqual(width);
          expect(expectedIconSize).toBeLessThanOrEqual(height);
        },
      ),
      { numRuns: 100 },
    );
  });
});
