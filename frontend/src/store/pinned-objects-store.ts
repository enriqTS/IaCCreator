import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { PickerItem } from '@/data/object-catalog';
import { createSafeStorage } from '@/utils/safe-storage';

export const MAX_PINNED_ITEMS = 24;
const STORAGE_KEY = 'pinned-picker-items';

export function pickerItemKey(item: Pick<PickerItem, 'name' | 'category'>): string {
  return `${item.category}|${item.name}`;
}

interface PinnedObjectsState {
  pinnedItems: PickerItem[];
  togglePin: (item: PickerItem) => void;
  clearPins: () => void;
}

export const usePinnedObjectsStore = create<PinnedObjectsState>()(
  persist(
    (set) => ({
      pinnedItems: [],

      togglePin: (item) =>
        set((state) => {
          const key = pickerItemKey(item);
          const without = state.pinnedItems.filter((p) => pickerItemKey(p) !== key);
          if (without.length !== state.pinnedItems.length) return { pinnedItems: without };
          return { pinnedItems: [...state.pinnedItems, item].slice(-MAX_PINNED_ITEMS) };
        }),

      clearPins: () => set({ pinnedItems: [] }),
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(() => createSafeStorage('local')),
      partialize: (state) => ({ pinnedItems: state.pinnedItems }),
    },
  ),
);
