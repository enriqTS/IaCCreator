import { useRecentlyUsedStore, MAX_RECENT_ITEMS } from '@/store/recently-used-store';
import type { PickerItem } from '@/components/toolbar/ObjectPickerMenu';

function makeItem(name: string, category = 'Shapes'): PickerItem {
  return { name, category, tool: 'pointer' };
}

describe('recently-used-store', () => {
  beforeEach(() => {
    // Reset store state between tests
    useRecentlyUsedStore.getState().clearRecentItems();
    sessionStorage.clear();
  });

  it('starts with an empty list', () => {
    expect(useRecentlyUsedStore.getState().recentItems).toEqual([]);
  });

  it('adds an item to the front', () => {
    const { addRecentItem } = useRecentlyUsedStore.getState();
    addRecentItem(makeItem('Rectangle'));
    addRecentItem(makeItem('Circle'));

    const items = useRecentlyUsedStore.getState().recentItems;
    expect(items[0].name).toBe('Circle');
    expect(items[1].name).toBe('Rectangle');
  });

  it('deduplicates by moving existing item to front', () => {
    const { addRecentItem } = useRecentlyUsedStore.getState();
    addRecentItem(makeItem('A'));
    addRecentItem(makeItem('B'));
    addRecentItem(makeItem('C'));
    // Re-add A — should move to front, not duplicate
    addRecentItem(makeItem('A'));

    const items = useRecentlyUsedStore.getState().recentItems;
    expect(items.map((i) => i.name)).toEqual(['A', 'C', 'B']);
    expect(items).toHaveLength(3);
  });

  it('deduplicates by name AND category', () => {
    const { addRecentItem } = useRecentlyUsedStore.getState();
    addRecentItem(makeItem('Rectangle', 'Shapes'));
    addRecentItem(makeItem('Rectangle', 'UML')); // different category — not a duplicate

    const items = useRecentlyUsedStore.getState().recentItems;
    expect(items).toHaveLength(2);
  });

  it('caps at MAX_RECENT_ITEMS', () => {
    const { addRecentItem } = useRecentlyUsedStore.getState();
    for (let i = 0; i < MAX_RECENT_ITEMS + 5; i++) {
      addRecentItem(makeItem(`Item-${i}`));
    }

    const items = useRecentlyUsedStore.getState().recentItems;
    expect(items).toHaveLength(MAX_RECENT_ITEMS);
    // Most recent should be first
    expect(items[0].name).toBe(`Item-${MAX_RECENT_ITEMS + 4}`);
  });

  it('exports MAX_RECENT_ITEMS as 12', () => {
    expect(MAX_RECENT_ITEMS).toBe(12);
  });

  it('clearRecentItems resets the list', () => {
    const { addRecentItem } = useRecentlyUsedStore.getState();
    addRecentItem(makeItem('A'));
    addRecentItem(makeItem('B'));

    useRecentlyUsedStore.getState().clearRecentItems();
    expect(useRecentlyUsedStore.getState().recentItems).toEqual([]);
  });
});
