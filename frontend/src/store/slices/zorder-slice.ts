/**
 * Stacking order of canvas objects.
 */

import type { StateCreator } from 'zustand';
import type { CanvasObject } from '@/types/diagram';
import type { DiagramStore } from './store-types';

export interface ZOrderSlice {
  // Z-order actions
  bringToFront: (id: string) => void;
  sendToBack: (id: string) => void;
  bringForward: (id: string) => void;
  sendBackward: (id: string) => void;
}

export const createZOrderSlice: StateCreator<DiagramStore, [], [], ZOrderSlice> = (set, get) => ({
    // --- Z-order actions ---

    bringToFront: (id: string): void => {
      const { canvasObjects } = get();
      const target = canvasObjects.get(id);
      if (!target) return;

      let maxZ = -Infinity;
      for (const obj of canvasObjects.values()) {
        if (obj.id !== id && obj.zIndex > maxZ) maxZ = obj.zIndex;
      }
      // If already on top (or only object), no-op
      if (canvasObjects.size <= 1 || target.zIndex > maxZ) return;

      const newZ = maxZ + 1;
      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(id, { ...target, zIndex: newZ } as CanvasObject);
        return { canvasObjects: next };
      });
    },

    sendToBack: (id: string): void => {
      const { canvasObjects } = get();
      const target = canvasObjects.get(id);
      if (!target) return;

      let minZ = Infinity;
      for (const obj of canvasObjects.values()) {
        if (obj.id !== id && obj.zIndex < minZ) minZ = obj.zIndex;
      }
      // If already at back (or only object), no-op
      if (canvasObjects.size <= 1 || target.zIndex < minZ) return;

      const newZ = minZ - 1;
      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(id, { ...target, zIndex: newZ } as CanvasObject);
        return { canvasObjects: next };
      });
    },

    bringForward: (id: string): void => {
      const { canvasObjects } = get();
      const target = canvasObjects.get(id);
      if (!target) return;

      // Find the object directly above (smallest zIndex greater than target's)
      let aboveObj: CanvasObject | null = null;
      for (const obj of canvasObjects.values()) {
        if (obj.id !== id && obj.zIndex > target.zIndex) {
          if (!aboveObj || obj.zIndex < aboveObj.zIndex) {
            aboveObj = obj;
          }
        }
      }
      if (!aboveObj) return; // Already on top

      // Swap zIndex values
      const targetNewZ = aboveObj.zIndex;
      const aboveNewZ = target.zIndex;
      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(id, { ...target, zIndex: targetNewZ } as CanvasObject);
        next.set(aboveObj!.id, { ...aboveObj!, zIndex: aboveNewZ } as CanvasObject);
        return { canvasObjects: next };
      });
    },

    sendBackward: (id: string): void => {
      const { canvasObjects } = get();
      const target = canvasObjects.get(id);
      if (!target) return;

      // Find the object directly below (largest zIndex less than target's)
      let belowObj: CanvasObject | null = null;
      for (const obj of canvasObjects.values()) {
        if (obj.id !== id && obj.zIndex < target.zIndex) {
          if (!belowObj || obj.zIndex > belowObj.zIndex) {
            belowObj = obj;
          }
        }
      }
      if (!belowObj) return; // Already at back

      // Swap zIndex values
      const targetNewZ = belowObj.zIndex;
      const belowNewZ = target.zIndex;
      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(id, { ...target, zIndex: targetNewZ } as CanvasObject);
        next.set(belowObj!.id, { ...belowObj!, zIndex: belowNewZ } as CanvasObject);
        return { canvasObjects: next };
      });
    },
});
