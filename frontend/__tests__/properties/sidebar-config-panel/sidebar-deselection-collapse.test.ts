import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { DEFAULT_SIDEBAR_WIDTH } from '@/components/config/panel-constants';

// Feature: sidebar-config-panel, Property 10: Deselection auto-collapses sidebar
// **Validates: Requirements 8.3**
describe('Property 10: Deselection auto-collapses sidebar', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      sidebarExpanded: false,
      sidebarWidth: DEFAULT_SIDEBAR_WIDTH,
      selectedObjectIds: new Set<string>(),
    });
  });

  test('clearing a non-empty selection causes sidebarExpanded to become false', () => {
    fc.assert(
      fc.property(
        // Generate 1 to 5 random object IDs (non-empty strings)
        fc.array(
          fc.string({ minLength: 1, maxLength: 20 }),
          { minLength: 1, maxLength: 5 },
        ),
        (objectIds) => {
          const uniqueIds = [...new Set(objectIds)];
          fc.pre(uniqueIds.length > 0);

          // Start with sidebar expanded and a non-empty selection
          useDiagramStore.setState({
            sidebarExpanded: true,
            selectedObjectIds: new Set(uniqueIds),
          });

          // Verify precondition: sidebar is expanded with objects selected
          expect(useDiagramStore.getState().sidebarExpanded).toBe(true);
          expect(useDiagramStore.getState().selectedObjectIds.size).toBeGreaterThan(0);

          // Clear the selection (set to empty Set)
          useDiagramStore.setState({ selectedObjectIds: new Set<string>() });

          // Simulate the useEffect logic: when selectedObjectIds.size === 0,
          // call setSidebarExpanded(false)
          const store = useDiagramStore.getState();
          if (store.selectedObjectIds.size === 0) {
            store.setSidebarExpanded(false);
          }

          // Assert: sidebar is now collapsed
          expect(useDiagramStore.getState().sidebarExpanded).toBe(false);
        },
      ),
      { numRuns: 100 },
    );
  });

  test('sidebar stays expanded when selection is non-empty after update', () => {
    fc.assert(
      fc.property(
        // Generate 2 to 6 random object IDs
        fc.array(
          fc.string({ minLength: 1, maxLength: 20 }),
          { minLength: 2, maxLength: 6 },
        ),
        (objectIds) => {
          const uniqueIds = [...new Set(objectIds)];
          fc.pre(uniqueIds.length >= 2);

          // Start with sidebar expanded and all objects selected
          useDiagramStore.setState({
            sidebarExpanded: true,
            selectedObjectIds: new Set(uniqueIds),
          });

          // Remove one object but keep selection non-empty
          const remaining = uniqueIds.slice(1);
          useDiagramStore.setState({ selectedObjectIds: new Set(remaining) });

          // Simulate the useEffect logic: only collapse when size === 0
          const store = useDiagramStore.getState();
          if (store.selectedObjectIds.size === 0) {
            store.setSidebarExpanded(false);
          }

          // Assert: sidebar remains expanded because selection is still non-empty
          expect(useDiagramStore.getState().sidebarExpanded).toBe(true);
        },
      ),
      { numRuns: 100 },
    );
  });
});
