import fc from 'fast-check';
import { useRecentlyUsedStore, MAX_RECENT_ITEMS } from '@/store/recently-used-store';
import type { PickerItem } from '@/components/toolbar/ObjectPickerMenu';

// Feature: architecture-search-panel, Property 6: Recently-used session persistence round-trip
// **Validates: Requirements 3.5**

const STORAGE_KEY = 'recently-used-picker-items';

/**
 * Arbitrary that generates a PickerItem suitable for persistence testing.
 */
const arbPickerItem: fc.Arbitrary<PickerItem> = fc.record({
  name: fc.string({ minLength: 1, maxLength: 20 }),
  category: fc.constantFrom('Shapes', 'UML', 'Text', 'Lines & Arrows', 'AWS: Compute', 'AWS: Storage'),
  icon: fc.option(fc.constant('/icons/test.svg'), { nil: undefined }),
  tool: fc.constant('pointer' as PickerItem['tool']),
});

function itemKey(item: PickerItem): string {
  return `${item.name}::${item.category}`;
}

describe('Property 6: Recently-used session persistence round-trip', () => {
  beforeEach(() => {
    useRecentlyUsedStore.getState().clearRecentItems();
    sessionStorage.clear();
  });

  test('for any recently-used list state, serializing to sessionStorage and deserializing produces an equivalent list', () => {
    fc.assert(
      fc.property(
        fc.array(arbPickerItem, { minLength: 0, maxLength: 12 }),
        (items) => {
          // Reset store and sessionStorage for each run
          useRecentlyUsedStore.getState().clearRecentItems();
          sessionStorage.clear();

          // Add items to the store (which auto-persists to sessionStorage)
          for (const item of items) {
            useRecentlyUsedStore.getState().addRecentItem(item);
          }

          // Capture the current store state
          const storeState = useRecentlyUsedStore.getState().recentItems;

          // Read the serialized data from sessionStorage
          const raw = sessionStorage.getItem(STORAGE_KEY);

          if (storeState.length === 0) {
            // Empty list: sessionStorage may be null or contain empty recentItems
            if (raw !== null) {
              const parsed = JSON.parse(raw);
              expect(parsed.state.recentItems).toEqual([]);
            }
            return;
          }

          // sessionStorage should have data
          expect(raw).not.toBeNull();
          const parsed = JSON.parse(raw!);

          // The persisted recentItems should match the store's state
          const persistedItems: PickerItem[] = parsed.state.recentItems;
          expect(persistedItems.length).toBe(storeState.length);

          // Verify each item matches by identity and order
          const persistedKeys = persistedItems.map(itemKey);
          const storeKeys = storeState.map(itemKey);
          expect(persistedKeys).toEqual(storeKeys);

          // Verify full item data round-trips correctly
          for (let i = 0; i < storeState.length; i++) {
            expect(persistedItems[i].name).toBe(storeState[i].name);
            expect(persistedItems[i].category).toBe(storeState[i].category);
            expect(persistedItems[i].tool).toEqual(storeState[i].tool);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
