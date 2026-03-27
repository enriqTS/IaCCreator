import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { MIN_SIDEBAR_WIDTH, MAX_SIDEBAR_WIDTH_RATIO, DEFAULT_SIDEBAR_WIDTH } from '@/components/config/panel-constants';

// Feature: sidebar-config-panel, Property 1: Width persistence round trip
// **Validates: Requirements 1.4, 1.11**
describe('Property 1: Width persistence round trip', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      sidebarExpanded: true,
      sidebarWidth: DEFAULT_SIDEBAR_WIDTH,
    });
  });

  test('set width → collapse → expand → width matches the originally set width', () => {
    const viewportWidth = window.innerWidth; // 1024 in jsdom
    const maxWidth = MAX_SIDEBAR_WIDTH_RATIO * viewportWidth;

    fc.assert(
      fc.property(
        fc.double({ min: MIN_SIDEBAR_WIDTH, max: maxWidth, noNaN: true, noDefaultInfinity: true }),
        (width) => {
          const store = useDiagramStore.getState();

          // 1. Set the sidebar width
          store.setSidebarWidth(width);
          const setWidth = useDiagramStore.getState().sidebarWidth;

          // 2. Collapse the sidebar
          store.setSidebarExpanded(false);
          expect(useDiagramStore.getState().sidebarExpanded).toBe(false);

          // 3. Expand the sidebar
          store.setSidebarExpanded(true);
          expect(useDiagramStore.getState().sidebarExpanded).toBe(true);

          // 4. Assert width is preserved across the collapse/expand cycle
          expect(useDiagramStore.getState().sidebarWidth).toBe(setWidth);
        },
      ),
      { numRuns: 100 },
    );
  });
});
