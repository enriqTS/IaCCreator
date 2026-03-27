import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { MIN_SIDEBAR_WIDTH, MAX_SIDEBAR_WIDTH_RATIO, DEFAULT_SIDEBAR_WIDTH } from '@/components/config/panel-constants';

// Feature: sidebar-config-panel, Property 3: Width clamping within bounds
// **Validates: Requirements 1.7, 1.8**
describe('Property 3: Width clamping within bounds', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      sidebarExpanded: false,
      sidebarWidth: DEFAULT_SIDEBAR_WIDTH,
    });
  });

  test('setSidebarWidth always clamps to [MIN_SIDEBAR_WIDTH, MAX_SIDEBAR_WIDTH_RATIO × viewportWidth]', () => {
    const viewportWidth = window.innerWidth; // 1024 in jsdom
    const maxWidth = MAX_SIDEBAR_WIDTH_RATIO * viewportWidth;

    fc.assert(
      fc.property(
        fc.oneof(
          // Negative values
          fc.double({ min: -1e6, max: -1, noNaN: true, noDefaultInfinity: true }),
          // Zero
          fc.constant(0),
          // Below minimum
          fc.double({ min: 1, max: MIN_SIDEBAR_WIDTH - 1, noNaN: true, noDefaultInfinity: true }),
          // Valid range
          fc.double({ min: MIN_SIDEBAR_WIDTH, max: maxWidth, noNaN: true, noDefaultInfinity: true }),
          // Above maximum
          fc.double({ min: maxWidth + 1, max: 1e6, noNaN: true, noDefaultInfinity: true }),
        ),
        (width) => {
          const store = useDiagramStore.getState();

          store.setSidebarWidth(width);

          const storedWidth = useDiagramStore.getState().sidebarWidth;

          // The stored width must always be within the valid bounds
          expect(storedWidth).toBeGreaterThanOrEqual(MIN_SIDEBAR_WIDTH);
          expect(storedWidth).toBeLessThanOrEqual(maxWidth);
        },
      ),
      { numRuns: 100 },
    );
  });

  test('setSidebarWidth clamps correctly across random viewport widths', () => {
    fc.assert(
      fc.property(
        // Viewport wide enough that maxWidth >= MIN_SIDEBAR_WIDTH (i.e. viewport >= 560)
        fc.integer({ min: Math.ceil(MIN_SIDEBAR_WIDTH / MAX_SIDEBAR_WIDTH_RATIO), max: 3840 }),
        // Random requested width (wide range including out-of-bounds)
        fc.double({ min: -1e4, max: 1e4, noNaN: true, noDefaultInfinity: true }),
        (viewportWidth, requestedWidth) => {
          // Mock window.innerWidth for this iteration
          Object.defineProperty(window, 'innerWidth', {
            value: viewportWidth,
            writable: true,
            configurable: true,
          });

          const maxWidth = MAX_SIDEBAR_WIDTH_RATIO * viewportWidth;
          const store = useDiagramStore.getState();

          store.setSidebarWidth(requestedWidth);

          const storedWidth = useDiagramStore.getState().sidebarWidth;

          expect(storedWidth).toBeGreaterThanOrEqual(MIN_SIDEBAR_WIDTH);
          expect(storedWidth).toBeLessThanOrEqual(maxWidth);
        },
      ),
      { numRuns: 100 },
    );
  });
});
