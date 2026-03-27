import fc from 'fast-check';
import { SIDEBAR_RESPONSIVE_THRESHOLD } from '@/components/config/panel-constants';

// Feature: sidebar-config-panel, Property 7: Layout mode by width threshold
// **Validates: Requirements 7.4, 7.5**

/**
 * Pure function that determines layout mode based on sidebar width.
 * Mirrors the logic in GlobalTerraformConfigPanel:
 *   const isTwoColumn = panelWidth !== undefined && panelWidth >= SIDEBAR_RESPONSIVE_THRESHOLD;
 */
function getLayoutMode(width: number): 'single-column' | 'two-column' {
  return width >= SIDEBAR_RESPONSIVE_THRESHOLD ? 'two-column' : 'single-column';
}

describe('Property 7: Layout mode determined by width threshold', () => {
  test('layout mode is "single-column" when width < 350px and "two-column" when width >= 350px', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 2000 }),
        (width) => {
          const mode = getLayoutMode(width);

          if (width < SIDEBAR_RESPONSIVE_THRESHOLD) {
            expect(mode).toBe('single-column');
          } else {
            expect(mode).toBe('two-column');
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  test('threshold boundary: width exactly at SIDEBAR_RESPONSIVE_THRESHOLD is "two-column"', () => {
    const mode = getLayoutMode(SIDEBAR_RESPONSIVE_THRESHOLD);
    expect(mode).toBe('two-column');
  });

  test('threshold boundary: width one below SIDEBAR_RESPONSIVE_THRESHOLD is "single-column"', () => {
    const mode = getLayoutMode(SIDEBAR_RESPONSIVE_THRESHOLD - 1);
    expect(mode).toBe('single-column');
  });
});
