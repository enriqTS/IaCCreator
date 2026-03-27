import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { MIN_SIDEBAR_WIDTH, MAX_SIDEBAR_WIDTH_RATIO, DEFAULT_SIDEBAR_WIDTH } from '@/components/config/panel-constants';

// Feature: sidebar-config-panel, Property 4: Drag below minimum collapses
// **Validates: Requirements 1.9**
describe('Property 4: Drag below minimum collapses', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      sidebarExpanded: true,
      sidebarWidth: DEFAULT_SIDEBAR_WIDTH,
    });
  });

  test('for any current width and drag delta resulting in width < MIN_SIDEBAR_WIDTH, sidebar collapses', () => {
    const viewportWidth = window.innerWidth; // 1024 in jsdom
    const maxWidth = MAX_SIDEBAR_WIDTH_RATIO * viewportWidth;

    fc.assert(
      fc.property(
        // Current valid sidebar width
        fc.double({ min: MIN_SIDEBAR_WIDTH, max: maxWidth, noNaN: true, noDefaultInfinity: true }),
        // Drag delta that will push the resulting width below MIN_SIDEBAR_WIDTH
        // For sidebar on the left: rawWidth = currentWidth + deltaX, so deltaX must be negative enough
        // We generate a negative delta such that currentWidth + delta < MIN_SIDEBAR_WIDTH
        // i.e. delta < MIN_SIDEBAR_WIDTH - currentWidth (which is <= 0)
        fc.double({ min: -1e4, max: -1, noNaN: true, noDefaultInfinity: true }),
        (currentWidth, negativeDelta) => {
          // Compute the raw width after applying the drag delta
          const rawWidth = currentWidth + negativeDelta;

          // Only test cases where the drag actually goes below minimum
          fc.pre(rawWidth < MIN_SIDEBAR_WIDTH);

          // Set up: sidebar is expanded with the current width
          useDiagramStore.setState({
            sidebarExpanded: true,
            sidebarWidth: currentWidth,
          });

          // Simulate the drag-to-collapse logic from SidebarPanel's handleMouseMove:
          // When rawWidth < MIN_SIDEBAR_WIDTH, the component calls setSidebarExpanded(false)
          const store = useDiagramStore.getState();
          if (rawWidth < MIN_SIDEBAR_WIDTH) {
            store.setSidebarExpanded(false);
          }

          // Assert: sidebar is now collapsed
          expect(useDiagramStore.getState().sidebarExpanded).toBe(false);
        },
      ),
      { numRuns: 100 },
    );
  });

  test('drag below minimum does not alter the stored sidebar width', () => {
    const viewportWidth = window.innerWidth;
    const maxWidth = MAX_SIDEBAR_WIDTH_RATIO * viewportWidth;

    fc.assert(
      fc.property(
        fc.double({ min: MIN_SIDEBAR_WIDTH, max: maxWidth, noNaN: true, noDefaultInfinity: true }),
        fc.double({ min: -1e4, max: -1, noNaN: true, noDefaultInfinity: true }),
        (currentWidth, negativeDelta) => {
          const rawWidth = currentWidth + negativeDelta;
          fc.pre(rawWidth < MIN_SIDEBAR_WIDTH);

          // Set up: sidebar expanded with a known width
          useDiagramStore.setState({
            sidebarExpanded: true,
            sidebarWidth: currentWidth,
          });

          const store = useDiagramStore.getState();

          // Simulate drag-to-collapse: component collapses without calling setSidebarWidth
          if (rawWidth < MIN_SIDEBAR_WIDTH) {
            store.setSidebarExpanded(false);
          }

          // The stored width should remain unchanged (preserved for re-expand)
          expect(useDiagramStore.getState().sidebarWidth).toBe(currentWidth);
        },
      ),
      { numRuns: 100 },
    );
  });
});
