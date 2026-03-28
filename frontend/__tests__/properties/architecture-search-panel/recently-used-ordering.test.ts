import fc from 'fast-check';
import { useRecentlyUsedStore } from '@/store/recently-used-store';
import type { PickerItem } from '@/components/toolbar/ObjectPickerMenu';

// Feature: architecture-search-panel, Property 4: Recently-used add and ordering
// **Validates: Requirements 3.2, 3.7**

/**
 * Arbitrary that generates a PickerItem with a unique name+category identity.
 */
const arbPickerItem: fc.Arbitrary<PickerItem> = fc.record({
  name: fc.string({ minLength: 1, maxLength: 20 }),
  category: fc.constantFrom('Shapes', 'UML', 'Text', 'Lines & Arrows', 'AWS: Compute', 'AWS: Storage'),
  icon: fc.option(fc.constant('/icons/test.svg'), { nil: undefined }),
  tool: fc.constant('pointer' as PickerItem['tool']),
});

/**
 * Helper: identity key for deduplication (name + category).
 */
function itemKey(item: PickerItem): string {
  return `${item.name}::${item.category}`;
}

describe('Property 4: Recently-used add and ordering', () => {
  beforeEach(() => {
    useRecentlyUsedStore.getState().clearRecentItems();
  });

  test('for any sequence of item additions, the list is in most-recent-first order with no duplicates and the last added item at index 0', () => {
    fc.assert(
      fc.property(
        fc.array(arbPickerItem, { minLength: 1, maxLength: 30 }),
        (items) => {
          // Reset store for each run
          useRecentlyUsedStore.getState().clearRecentItems();

          // Add all items in sequence
          for (const item of items) {
            useRecentlyUsedStore.getState().addRecentItem(item);
          }

          const recentItems = useRecentlyUsedStore.getState().recentItems;

          // 1. The most recently added item is always at index 0
          const lastAdded = items[items.length - 1];
          expect(recentItems[0].name).toBe(lastAdded.name);
          expect(recentItems[0].category).toBe(lastAdded.category);

          // 2. No duplicates by name+category
          const keys = recentItems.map(itemKey);
          const uniqueKeys = new Set(keys);
          expect(keys.length).toBe(uniqueKeys.size);

          // 3. Items appear in most-recent-first order
          // Build expected order: walk items in reverse, keeping first occurrence
          const seen = new Set<string>();
          const expectedOrder: PickerItem[] = [];
          for (let i = items.length - 1; i >= 0; i--) {
            const key = itemKey(items[i]);
            if (!seen.has(key)) {
              seen.add(key);
              expectedOrder.push(items[i]);
            }
          }
          // The store caps at MAX_RECENT_ITEMS (12), so slice expected to match
          const expectedKeys = expectedOrder.map(itemKey).slice(0, 12);
          const actualKeys = recentItems.map(itemKey);
          expect(actualKeys).toEqual(expectedKeys);
        }
      ),
      { numRuns: 100 }
    );
  });
});
