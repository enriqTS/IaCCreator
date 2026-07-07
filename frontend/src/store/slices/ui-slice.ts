/**
 * UI Slice — Active tool, panel dimensions, routing mode, and global config.
 *
 * This file defines the public contract (UISlice interface) for the
 * UI concerns of the diagram store. The actual implementation will be
 * extracted from diagram-store.ts in a subsequent pass (task 10.6).
 *
 * Requirements: 7.1, 7.8
 */

import type { StateCreator } from 'zustand';
import type { Tool, RoutingMode } from '@/types/diagram';
import type { GlobalTerraformConfig } from '@/types/terraform-variables';

export interface UISlice {
  activeTool: Tool;
  setActiveTool: (tool: Tool) => void;
  configPanelHeight: number;
  setConfigPanelHeight: (height: number) => void;
  sidebarWidth: number;
  setSidebarWidth: (width: number) => void;
  globalRoutingMode: RoutingMode;
  setGlobalRoutingMode: (mode: RoutingMode) => void;
  globalTerraformConfig: GlobalTerraformConfig;
  setGlobalTerraformConfig: (config: GlobalTerraformConfig) => void;
}

export type CreateUISlice = StateCreator<UISlice, [], [], UISlice>;
