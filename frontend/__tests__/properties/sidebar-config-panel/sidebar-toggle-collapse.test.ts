import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { MIN_SIDEBAR_WIDTH, MAX_SIDEBAR_WIDTH_RATIO, DEFAULT_SIDEBAR_WIDTH } from '@/components/config/panel-constants';

// Feature: sidebar-config-panel, Property 2: Toggle collapses expanded panel
// **Validates: Requirements 1.5**
describe('Property 2: Toggle collapses expanded panel', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      sidebarExpanded: true,
      sidebarWidth: DEFAULT_SIDEBAR_WIDTH,
    });
  });

  test('calling toggleSidebar on an expanded sidebar always results in sidebarExpanded being false', () => {
    const viewportWidth = window.innerWidth; // 1024 in jsdom
    const maxWidth = MAX_SIDEBAR_WIDTH_RATIO * viewportWidth;

    fc.assert(
      fc.property(
        fc.double({ min: MIN_SIDEBAR_WIDTH, max: maxWidth, noNaN: true, noDefaultInfinity: true }),
        (width) => {
          // Set up: sidebar is expanded with a random valid width
          useDiagramStore.setState({ sidebarExpanded: true, sidebarWidth: width });

          const store = useDiagramStore.getState();

          // Act: toggle the sidebar
          store.toggleSidebar();

          // Assert: sidebar is now collapsed
          expect(useDiagramStore.getState().sidebarExpanded).toBe(false);
        },
      ),
      { numRuns: 100 },
    );
  });
});
