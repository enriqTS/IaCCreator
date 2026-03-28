import { create } from 'zustand';
import { persist, createJSONStorage, type StateStorage } from 'zustand/middleware';
import type { PickerItem } from '@/components/toolbar/ObjectPickerMenu';

export const MAX_RECENT_ITEMS = 12;
const STORAGE_KEY = 'recently-used-picker-items';

/**
 * Creates a safe sessionStorage wrapper that falls back to in-memory
 * storage when sessionStorage is unavailable (e.g. private browsing).
 */
function createSafeStorage(): StateStorage {
  // Test sessionStorage availability once upfront
  let storageAvailable = false;
  try {
    const testKey = '__storage_test__';
    sessionStorage.setItem(testKey, '1');
    sessionStorage.removeItem(testKey);
    storageAvailable = true;
  } catch {
    storageAvailable = false;
  }

  if (storageAvailable) {
    return {
      getItem: (name: string) => {
        try {
          return sessionStorage.getItem(name);
        } catch {
          return null;
        }
      },
      setItem: (name: string, value: string) => {
        try {
          sessionStorage.setItem(name, value);
        } catch {
          // Silently fail — in-memory state still works
        }
      },
      removeItem: (name: string) => {
        try {
          sessionStorage.removeItem(name);
        } catch {
          // Silently fail
        }
      },
    };
  }

  // In-memory fallback when sessionStorage is completely unavailable
  const memoryStore = new Map<string, string>();
  return {
    getItem: (name: string) => memoryStore.get(name) ?? null,
    setItem: (name: string, value: string) => { memoryStore.set(name, value); },
    removeItem: (name: string) => { memoryStore.delete(name); },
  };
}

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
      storage: createJSONStorage(() => createSafeStorage()),
      // Only persist the data, not the actions
      partialize: (state) => ({ recentItems: state.recentItems }),
    },
  ),
);
