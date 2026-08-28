/**
 * Project identity, environments and Terraform variables.
 */

import type { StateCreator } from 'zustand';
import type { ArchitectureBlock, EnvironmentConfig } from '@/types/diagram';
import type { GlobalTerraformConfig } from '@/types/terraform-variables';
import { EMPTY_GLOBAL_CONFIG } from '@/types/terraform-variables';
import type { DiagramStore } from './store-types';

export interface ProjectSlice {
  // Project state
  projectName: string;
  environments: EnvironmentConfig[];
  activeEnvironmentName: string | null;
  setProjectName: (name: string) => void;
  setEnvironments: (envs: EnvironmentConfig[]) => void;
  setActiveEnvironment: (name: string | null) => void;

  // Terraform variables
  setTerraformVariable: (objectId: string, varName: string, value: string | number | boolean) => void;
  setTerraformVariables: (objectId: string, vars: Record<string, string | number | boolean>) => void;
  globalTerraformConfig: GlobalTerraformConfig;
  updateGlobalTerraformConfig: (updates: Partial<GlobalTerraformConfig>) => void;
}

export const createProjectSlice: StateCreator<DiagramStore, [], [], ProjectSlice> = (set, get) => ({
    // --- Project state ---
    projectName: '',
    environments: [] as EnvironmentConfig[],
    activeEnvironmentName: null,

    setProjectName: (name: string): void => {
      set({ projectName: name });
    },

    setEnvironments: (envs: EnvironmentConfig[]): void => {
      set((state) => ({
        environments: envs,
        activeEnvironmentName: state.activeEnvironmentName
          && envs.some((environment) => environment.name === state.activeEnvironmentName)
          ? state.activeEnvironmentName
          : envs[0]?.name ?? null,
      }));
    },

    setActiveEnvironment: (name: string | null): void => {
      set((state) => ({
        activeEnvironmentName: name && state.environments.some((environment) => environment.name === name)
          ? name
          : null,
      }));
    },

    // --- Terraform variables ---
    globalTerraformConfig: structuredClone(EMPTY_GLOBAL_CONFIG),

    setTerraformVariable: (objectId: string, varName: string, value: string | number | boolean): void => {
      const existing = get().canvasObjects.get(objectId);
      if (!existing || existing.objectType !== 'architecture-block') return;
      get().pushHistory();
      set((state) => {
        const next = new Map(state.canvasObjects);
        const block = state.canvasObjects.get(objectId) as ArchitectureBlock;
        next.set(objectId, {
          ...block,
          terraformVariables: { ...block.terraformVariables, [varName]: value },
        });
        return { canvasObjects: next };
      });
    },

    setTerraformVariables: (objectId: string, vars: Record<string, string | number | boolean>): void => {
      const existing = get().canvasObjects.get(objectId);
      if (!existing || existing.objectType !== 'architecture-block') return;
      get().pushHistory();
      set((state) => {
        const next = new Map(state.canvasObjects);
        const block = state.canvasObjects.get(objectId) as ArchitectureBlock;
        next.set(objectId, {
          ...block,
          terraformVariables: { ...block.terraformVariables, ...vars },
        });
        return { canvasObjects: next };
      });
    },

    updateGlobalTerraformConfig: (updates: Partial<GlobalTerraformConfig>): void => {
      set((state) => ({
        globalTerraformConfig: { ...state.globalTerraformConfig, ...updates },
      }));
    },
});
