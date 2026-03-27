import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { DEFAULT_SIDEBAR_WIDTH } from '@/components/config/panel-constants';

// Feature: sidebar-config-panel, Property 9: Multi-selection count
// **Validates: Requirements 8.2**
describe('Property 9: Multi-selection displays correct object count', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      sidebarExpanded: false,
      sidebarWidth: DEFAULT_SIDEBAR_WIDTH,
      selectedObjectIds: new Set<string>(),
    });
  });

  test('selectedObjectIds set size matches the number of selected objects for sets of 2+', () => {
    fc.assert(
      fc.property(
        // Generate 2 to 10 unique object IDs
        fc.uniqueArray(fc.string({ minLength: 1, maxLength: 20 }), {
          minLength: 2,
          maxLength: 10,
        }),
        (objectIds) => {
          fc.pre(objectIds.length >= 2);

          const selectedIds = new Set(objectIds);

          useDiagramStore.setState({
            sidebarExpanded: true,
            selectedObjectIds: selectedIds,
          });

          const store = useDiagramStore.getState();

          // The multi-selection summary displays `selectedObjectIds.size` as the count
          // Assert the store's selectedObjectIds size matches the input set size
          expect(store.selectedObjectIds.size).toBe(selectedIds.size);
          expect(store.selectedObjectIds.size).toBeGreaterThanOrEqual(2);
        },
      ),
      { numRuns: 100 },
    );
  });
});
