import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { LAYOUT_PREFS_STORAGE_KEY } from '@/components/config/panel-constants';

interface LayoutPreferencesState {
  toolbarPosition: 'top' | 'bottom';
  gridCellSize: number;
  snapToGridEnabled: boolean;
  alignmentGuidesEnabled: boolean;
  objectSidebarCollapsed: boolean;
  objectSidebarPosition: 'left' | 'right';
  objectSidebarWidth: number;
  setToolbarPosition: (position: 'top' | 'bottom') => void;
  setGridCellSize: (size: number) => void;
  setSnapToGridEnabled: (enabled: boolean) => void;
  setAlignmentGuidesEnabled: (enabled: boolean) => void;
  setObjectSidebarCollapsed: (collapsed: boolean) => void;
  setObjectSidebarPosition: (position: 'left' | 'right') => void;
  setObjectSidebarWidth: (width: number) => void;
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
      objectSidebarPosition: 'left',
      objectSidebarWidth: 240,
      setToolbarPosition: (position) => set({ toolbarPosition: position }),
      setGridCellSize: (size) => set({ gridCellSize: Math.max(5, Math.min(100, size)) }),
      setSnapToGridEnabled: (enabled) => set({ snapToGridEnabled: enabled }),
      setAlignmentGuidesEnabled: (enabled) => set({ alignmentGuidesEnabled: enabled }),
      setObjectSidebarCollapsed: (collapsed) => set({ objectSidebarCollapsed: collapsed }),
      setObjectSidebarPosition: (position) => set({ objectSidebarPosition: position }),
      setObjectSidebarWidth: (width) => set({ objectSidebarWidth: Math.max(200, Math.min(480, width)) }),
      toggleObjectSidebar: () =>
        set((state) => ({ objectSidebarCollapsed: !state.objectSidebarCollapsed })),
    }),
    {
      name: LAYOUT_PREFS_STORAGE_KEY,
    },
  ),
);
