import fc from 'fast-check';
import { useRecentlyUsedStore, MAX_RECENT_ITEMS } from '@/store/recently-used-store';
import type { PickerItem } from '@/components/toolbar/ObjectPickerMenu';

// Feature: architecture-search-panel, Property 5: Recently-used max capacity with eviction
// **Validates: Requirements 3.3, 3.4**

/**
 * Arbitrary that generates a list of distinct PickerItems (unique by name+category).
 * Always produces at least 13 items to exceed MAX_RECENT_ITEMS (12).
 */
function arbDistinctPickerItems(min: number, max: number): fc.Arbitrary<PickerItem[]> {
  return fc
    .uniqueArray(
      fc.record({
        name: fc.string({ minLength: 1, maxLength: 20 }),
        category: fc.constantFrom('Shapes', 'UML', 'Text', 'Lines & Arrows', 'AWS: Compute', 'AWS: Storage'),
      }),
      {
        minLength: min,
        maxLength: max,
        comparator: (a, b) => a.name === b.name && a.category === b.category,
      },
    )
    .map((identities) =>
      identities.map((id) => ({
        ...id,
        icon: undefined,
        tool: 'pointer' as PickerItem['tool'],
      })),
    );
}

function itemKey(item: PickerItem): string {
  return `${item.name}::${item.category}`;
}

describe('Property 5: Recently-used max capacity with eviction', () => {
  beforeEach(() => {
    useRecentlyUsedStore.getState().clearRecentItems();
  });

  test('for any sequence of more than 12 distinct items, the list contains exactly 12 most recently added items', () => {
    fc.assert(
      fc.property(
        arbDistinctPickerItems(MAX_RECENT_ITEMS + 1, 30),
        (items) => {
          // Reset store for each run
          useRecentlyUsedStore.getState().clearRecentItems();

          // Add all items in sequence
          for (const item of items) {
            useRecentlyUsedStore.getState().addRecentItem(item);
          }

          const recentItems = useRecentlyUsedStore.getState().recentItems;

          // 1. List length is exactly MAX_RECENT_ITEMS
          expect(recentItems.length).toBe(MAX_RECENT_ITEMS);

          // 2. The 12 items present are the 12 most recently added
          const expectedItems = items.slice(-MAX_RECENT_ITEMS).reverse();
          const expectedKeys = expectedItems.map(itemKey);
          const actualKeys = recentItems.map(itemKey);
          expect(actualKeys).toEqual(expectedKeys);

          // 3. The oldest items were evicted (not present in the list)
          const evictedItems = items.slice(0, items.length - MAX_RECENT_ITEMS);
          const recentKeySet = new Set(actualKeys);
          for (const evicted of evictedItems) {
            expect(recentKeySet.has(itemKey(evicted))).toBe(false);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
