import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { LAYOUT_PREFS_STORAGE_KEY } from '@/components/config/panel-constants';

interface LayoutPreferencesState {
  sidebarSide: 'left' | 'right';
  toolbarPosition: 'top' | 'bottom';
  gridCellSize: number;
  snapToGridEnabled: boolean;
  alignmentGuidesEnabled: boolean;
  setSidebarSide: (side: 'left' | 'right') => void;
  setToolbarPosition: (position: 'top' | 'bottom') => void;
  setGridCellSize: (size: number) => void;
  setSnapToGridEnabled: (enabled: boolean) => void;
  setAlignmentGuidesEnabled: (enabled: boolean) => void;
}

export const useLayoutPreferencesStore = create<LayoutPreferencesState>()(
  persist(
    (set) => ({
      sidebarSide: 'right',
      toolbarPosition: 'top',
      gridCellSize: 20,
      snapToGridEnabled: true,
      alignmentGuidesEnabled: true,
      setSidebarSide: (side) => set({ sidebarSide: side }),
      setToolbarPosition: (position) => set({ toolbarPosition: position }),
      setGridCellSize: (size) => set({ gridCellSize: Math.max(5, Math.min(100, size)) }),
      setSnapToGridEnabled: (enabled) => set({ snapToGridEnabled: enabled }),
      setAlignmentGuidesEnabled: (enabled) => set({ alignmentGuidesEnabled: enabled }),
    }),
    {
      name: LAYOUT_PREFS_STORAGE_KEY,
    },
  ),
);
