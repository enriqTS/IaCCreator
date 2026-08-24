import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { PickerItem } from '@/data/object-catalog';
import { createSafeStorage } from '@/utils/safe-storage';

export const MAX_RECENT_ITEMS = 12;
const STORAGE_KEY = 'recently-used-picker-items';

interface RecentlyUsedState {
  recentItems: PickerItem[];
  addRecentItem: (item: PickerItem) => void;
  clearRecentItems: () => void;
}

export const useRecentlyUsedStore = create<RecentlyUsedState>()(
  persist(
    (set) => ({
      recentItems: [],

      addRecentItem: (item) =>
        set((state) => {
          // Remove existing duplicate (match by name + category)
          const filtered = state.recentItems.filter(
            (existing) => !(existing.name === item.name && existing.category === item.category),
          );
          // Prepend the new item and cap at MAX_RECENT_ITEMS
          const updated = [item, ...filtered].slice(0, MAX_RECENT_ITEMS);
          return { recentItems: updated };
        }),

      clearRecentItems: () => set({ recentItems: [] }),
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(() => createSafeStorage('session')),
      // Only persist the data, not the actions
      partialize: (state) => ({ recentItems: state.recentItems }),
    },
  ),
);
