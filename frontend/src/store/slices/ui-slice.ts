/**
 * Editor chrome — active tool, panels and routing mode.
 */

import type { StateCreator } from 'zustand';
import { DEFAULT_PANEL_HEIGHT, DEFAULT_SIDEBAR_WIDTH, MAX_PANEL_HEIGHT_RATIO, MAX_SIDEBAR_WIDTH_RATIO, MIN_PANEL_HEIGHT, MIN_SIDEBAR_WIDTH } from '@/components/config/panel-constants';
import type { RoutingMode, Tool } from '@/types/diagram';
import type { DiagramStore } from './store-types';

export interface UISlice {
  // UI state
  activeTool: Tool;
  setActiveTool: (tool: Tool) => void;
  selectedConnectorId: string | null;
  selectConnector: (id: string | null) => void;
  pendingConnectorSourceId: string | null;

  // Bottom panel state
  bottomPanelExpanded: boolean;
  bottomPanelHeight: number;
  setBottomPanelExpanded: (expanded: boolean) => void;
  setBottomPanelHeight: (height: number) => void;
  toggleBottomPanel: () => void;

  // Sidebar panel state
  sidebarExpanded: boolean;
  sidebarWidth: number;
  setSidebarExpanded: (expanded: boolean) => void;
  setSidebarWidth: (width: number) => void;
  toggleSidebar: () => void;

  // Global routing mode
  globalRoutingMode: RoutingMode;
  setGlobalRoutingMode: (mode: RoutingMode) => void;
}

export const createUISlice: StateCreator<DiagramStore, [], [], UISlice> = (set) => ({
    // --- UI state ---
    activeTool: 'pointer' as Tool,
    selectedConnectorId: null,
    pendingConnectorSourceId: null,

    setActiveTool: (tool: Tool): void => {
      set({ activeTool: tool });
    },

    selectConnector: (id: string | null): void => {
      set({ selectedConnectorId: id });
    },

    // --- Bottom panel state ---
    bottomPanelExpanded: false,
    bottomPanelHeight: DEFAULT_PANEL_HEIGHT,

    setBottomPanelExpanded: (expanded: boolean): void => {
      set({ bottomPanelExpanded: expanded });
    },

    setBottomPanelHeight: (height: number): void => {
      const maxHeight = MAX_PANEL_HEIGHT_RATIO * window.innerHeight;
      const clamped = Math.min(Math.max(height, MIN_PANEL_HEIGHT), maxHeight);
      set({ bottomPanelHeight: clamped });
    },

    toggleBottomPanel: (): void => {
      set((state) => ({ bottomPanelExpanded: !state.bottomPanelExpanded }));
    },

    // --- Sidebar panel state ---
    sidebarExpanded: false,
    sidebarWidth: DEFAULT_SIDEBAR_WIDTH,

    setSidebarExpanded: (expanded: boolean): void => {
      set({ sidebarExpanded: expanded });
    },

    setSidebarWidth: (width: number): void => {
      const maxWidth = MAX_SIDEBAR_WIDTH_RATIO * window.innerWidth;
      const clamped = Math.min(Math.max(width, MIN_SIDEBAR_WIDTH), maxWidth);
      set({ sidebarWidth: clamped });
    },

    toggleSidebar: (): void => {
      set((state) => ({ sidebarExpanded: !state.sidebarExpanded }));
    },

    // --- Global routing mode ---
    globalRoutingMode: 'orthogonal' as RoutingMode,

    setGlobalRoutingMode: (mode: RoutingMode): void => {
      set({ globalRoutingMode: mode });
    },
});
