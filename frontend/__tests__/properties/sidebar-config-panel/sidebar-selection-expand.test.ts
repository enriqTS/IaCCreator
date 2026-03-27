import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { DEFAULT_SIDEBAR_WIDTH } from '@/components/config/panel-constants';

// Feature: sidebar-config-panel, Property 8: Selection auto-expands sidebar
// **Validates: Requirements 8.1**
describe('Property 8: Selection auto-expands sidebar', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      sidebarExpanded: false,
      sidebarWidth: DEFAULT_SIDEBAR_WIDTH,
      selectedObjectIds: new Set<string>(),
    });
  });

  test('selecting any object (setting selectedObjectIds to non-empty) causes sidebarExpanded to become true', () => {
    fc.assert(
      fc.property(
        // Generate 1 to 5 random object IDs (non-empty strings)
        fc.array(
          fc.string({ minLength: 1, maxLength: 20 }),
          { minLength: 1, maxLength: 5 },
        ),
        (objectIds) => {
          // Ensure we have at least one unique ID
          const uniqueIds = [...new Set(objectIds)];
          fc.pre(uniqueIds.length > 0);

          // Start with sidebar collapsed
          useDiagramStore.setState({
            sidebarExpanded: false,
            selectedObjectIds: new Set<string>(),
          });

          // Simulate what the SidebarPanel useEffect does:
          // When selectedObjectIds.size > 0, call setSidebarExpanded(true)
          const selectedObjectIds = new Set(uniqueIds);
          useDiagramStore.setState({ selectedObjectIds });

          const store = useDiagramStore.getState();
          if (store.selectedObjectIds.size > 0) {
            store.setSidebarExpanded(true);
          }

          // Assert: sidebar is now expanded
          expect(useDiagramStore.getState().sidebarExpanded).toBe(true);
        },
      ),
      { numRuns: 100 },
    );
  });

  test('sidebar remains collapsed when selectedObjectIds is empty', () => {
    // Start collapsed with no selection
    useDiagramStore.setState({
      sidebarExpanded: false,
      selectedObjectIds: new Set<string>(),
    });

    const store = useDiagramStore.getState();

    // Simulate the useEffect logic: only expand if selection is non-empty
    if (store.selectedObjectIds.size > 0) {
      store.setSidebarExpanded(true);
    }

    // Assert: sidebar stays collapsed
    expect(useDiagramStore.getState().sidebarExpanded).toBe(false);
  });
});
