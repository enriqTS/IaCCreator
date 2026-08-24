import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { LAYOUT_PREFS_STORAGE_KEY } from '@/components/config/panel-constants';

interface LayoutPreferencesState {
  toolbarPosition: 'top' | 'bottom';
  gridCellSize: number;
  snapToGridEnabled: boolean;
  alignmentGuidesEnabled: boolean;
  objectSidebarCollapsed: boolean;
  setToolbarPosition: (position: 'top' | 'bottom') => void;
  setGridCellSize: (size: number) => void;
  setSnapToGridEnabled: (enabled: boolean) => void;
  setAlignmentGuidesEnabled: (enabled: boolean) => void;
  setObjectSidebarCollapsed: (collapsed: boolean) => void;
  toggleObjectSidebar: () => void;
}

export const useLayoutPreferencesStore = create<LayoutPreferencesState>()(
  persist(
    (set) => ({
      toolbarPosition: 'top',
      gridCellSize: 20,
      snapToGridEnabled: true,
      alignmentGuidesEnabled: true,
      objectSidebarCollapsed: false,
      setToolbarPosition: (position) => set({ toolbarPosition: position }),
      setGridCellSize: (size) => set({ gridCellSize: Math.max(5, Math.min(100, size)) }),
      setSnapToGridEnabled: (enabled) => set({ snapToGridEnabled: enabled }),
      setAlignmentGuidesEnabled: (enabled) => set({ alignmentGuidesEnabled: enabled }),
      setObjectSidebarCollapsed: (collapsed) => set({ objectSidebarCollapsed: collapsed }),
      toggleObjectSidebar: () =>
        set((state) => ({ objectSidebarCollapsed: !state.objectSidebarCollapsed })),
    }),
    {
      name: LAYOUT_PREFS_STORAGE_KEY,
    },
  ),
);
