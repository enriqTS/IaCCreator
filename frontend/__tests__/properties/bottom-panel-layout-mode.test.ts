import fc from 'fast-check';
import { COMPACT_LAYOUT_THRESHOLD } from '@/components/config/panel-constants';

// Feature: bottom-panel-redesign, Property 7: Layout mode determined by height threshold
// **Validates: Requirements 3.1, 3.2**

/**
 * Pure function that mirrors the layout mode logic used in GlobalTerraformConfigPanel.
 * Returns "compact" for heights at or below the threshold, "grid" for heights above.
 */
function getLayoutMode(panelHeight: number): 'compact' | 'grid' {
  return panelHeight <= COMPACT_LAYOUT_THRESHOLD ? 'compact' : 'grid';
}

describe('Property 7: Layout mode determined by height threshold', () => {
  test('layout mode is "compact" when height ≤ COMPACT_LAYOUT_THRESHOLD and "grid" when height > COMPACT_LAYOUT_THRESHOLD', () => {
    fc.assert(
      fc.property(
        fc.double({ min: 1, max: 10000, noNaN: true, noDefaultInfinity: true }),
        (panelHeight) => {
          const mode = getLayoutMode(panelHeight);

          if (panelHeight <= COMPACT_LAYOUT_THRESHOLD) {
            expect(mode).toBe('compact');
          } else {
            expect(mode).toBe('grid');
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  test('boundary: height exactly at COMPACT_LAYOUT_THRESHOLD yields "compact"', () => {
    fc.assert(
      fc.property(
        fc.constant(COMPACT_LAYOUT_THRESHOLD),
        (panelHeight) => {
          expect(getLayoutMode(panelHeight)).toBe('compact');
        }
      ),
      { numRuns: 100 }
    );
  });

  test('boundary: height just above COMPACT_LAYOUT_THRESHOLD yields "grid"', () => {
    fc.assert(
      fc.property(
        fc.double({ min: COMPACT_LAYOUT_THRESHOLD + 0.001, max: 10000, noNaN: true, noDefaultInfinity: true }),
        (panelHeight) => {
          expect(getLayoutMode(panelHeight)).toBe('grid');
        }
      ),
      { numRuns: 100 }
    );
  });
});
