import fc from 'fast-check';
import { useLayoutPreferencesStore } from '@/store/layout-preferences-store';
import { LAYOUT_PREFS_STORAGE_KEY } from '@/components/config/panel-constants';

// Feature: sidebar-config-panel, Property 5: Layout preferences persistence round trip
// **Validates: Requirements 2.4, 4.4, 9.1, 9.2, 9.4**
describe('Property 5: Layout preferences persistence round trip', () => {
  beforeEach(() => {
    localStorage.clear();
    useLayoutPreferencesStore.setState({
      sidebarSide: 'right',
      toolbarPosition: 'top',
    });
  });

  test('write layout preferences to store → read from localStorage → values match', () => {
    const sidebarSideArb = fc.constantFrom<'left' | 'right'>('left', 'right');
    const toolbarPositionArb = fc.constantFrom<'top' | 'bottom'>('top', 'bottom');

    fc.assert(
      fc.property(sidebarSideArb, toolbarPositionArb, (sidebarSide, toolbarPosition) => {
        const store = useLayoutPreferencesStore.getState();

        // 1. Write preferences to the store
        store.setSidebarSide(sidebarSide);
        store.setToolbarPosition(toolbarPosition);

        // 2. Verify store state matches what was set
        const storeState = useLayoutPreferencesStore.getState();
        expect(storeState.sidebarSide).toBe(sidebarSide);
        expect(storeState.toolbarPosition).toBe(toolbarPosition);

        // 3. Read from localStorage and verify persistence
        const raw = localStorage.getItem(LAYOUT_PREFS_STORAGE_KEY);
        expect(raw).not.toBeNull();

        const persisted = JSON.parse(raw!);
        expect(persisted.state.sidebarSide).toBe(sidebarSide);
        expect(persisted.state.toolbarPosition).toBe(toolbarPosition);
      }),
      { numRuns: 100 },
    );
  });
});
