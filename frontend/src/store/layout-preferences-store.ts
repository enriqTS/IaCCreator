import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { LAYOUT_PREFS_STORAGE_KEY } from '@/components/config/panel-constants';

interface LayoutPreferencesState {
  sidebarSide: 'left' | 'right';
  toolbarPosition: 'top' | 'bottom';
  setSidebarSide: (side: 'left' | 'right') => void;
  setToolbarPosition: (position: 'top' | 'bottom') => void;
}

export const useLayoutPreferencesStore = create<LayoutPreferencesState>()(
  persist(
    (set) => ({
      sidebarSide: 'right',
      toolbarPosition: 'top',
      setSidebarSide: (side) => set({ sidebarSide: side }),
      setToolbarPosition: (position) => set({ toolbarPosition: position }),
    }),
    {
      name: LAYOUT_PREFS_STORAGE_KEY,
    },
  ),
);
