/**
 * Editor chrome — active tool, panels and routing mode.
 */

import type { StateCreator } from 'zustand';
import { DEFAULT_PANEL_HEIGHT, MAX_PANEL_HEIGHT_RATIO, MIN_PANEL_HEIGHT } from '@/components/config/panel-constants';
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

  // Configuration overlay — opened deliberately, never by selection alone
  configOverlayTargetId: string | null;
  openConfigOverlay: (objectId: string) => void;
  closeConfigOverlay: () => void;

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

    // --- Configuration overlay ---
    configOverlayTargetId: null,

    openConfigOverlay: (objectId: string): void => {
      set({ configOverlayTargetId: objectId });
    },

    closeConfigOverlay: (): void => {
      set({ configOverlayTargetId: null });
    },

    // --- Global routing mode ---
    globalRoutingMode: 'orthogonal' as RoutingMode,

    setGlobalRoutingMode: (mode: RoutingMode): void => {
      set({ globalRoutingMode: mode });
    },
});
