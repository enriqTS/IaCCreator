/**
 * Pan, zoom and fitting the diagram to the screen.
 */

import type { StateCreator } from 'zustand';
import type { Point, Viewport } from '@/types/diagram';
import { getObjectBounds } from '@/types/diagram';
import { animateViewport, cancelViewportAnimation, zoomAtPoint } from '@/utils/viewport';
import type { DiagramStore } from './store-types';

export interface ViewportSlice {
  // Fit to screen
  fitToScreen: (containerRect: { width: number; height: number }) => void;

  // Viewport state
  viewport: Viewport;
  pan: (dx: number, dy: number) => void;
  zoom: (factor: number, center: Point) => void;
}

export const createViewportSlice: StateCreator<DiagramStore, [], [], ViewportSlice> = (set, get) => ({
    // --- Fit to screen ---

    fitToScreen: (containerRect: { width: number; height: number }): void => {
      const { canvasObjects } = get();
      if (canvasObjects.size === 0) return;

      const PADDING = 40;

      // Compute bounding box of all objects
      let minX = Infinity;
      let minY = Infinity;
      let maxX = -Infinity;
      let maxY = -Infinity;

      for (const obj of canvasObjects.values()) {
        const bounds = getObjectBounds(obj);
        minX = Math.min(minX, bounds.x);
        minY = Math.min(minY, bounds.y);
        maxX = Math.max(maxX, bounds.x + bounds.width);
        maxY = Math.max(maxY, bounds.y + bounds.height);
      }

      const contentWidth = maxX - minX;
      const contentHeight = maxY - minY;

      // Available space after padding
      const availableWidth = containerRect.width - PADDING * 2;
      const availableHeight = containerRect.height - PADDING * 2;

      if (availableWidth <= 0 || availableHeight <= 0) return;

      // Calculate scale to fit
      let scale = Math.min(
        availableWidth / contentWidth,
        availableHeight / contentHeight
      );

      // Clamp scale to 0.1-5.0
      scale = Math.max(0.1, Math.min(5.0, scale));

      // Center the content: offset so that the center of the bounding box maps to the center of the container
      const contentCenterX = (minX + maxX) / 2;
      const contentCenterY = (minY + maxY) / 2;

      const offsetX = containerRect.width / 2 - contentCenterX * scale;
      const offsetY = containerRect.height / 2 - contentCenterY * scale;

      const target = { offsetX, offsetY, scale };
      animateViewport(
        () => get().viewport,
        (viewport) => set({ viewport }),
        target,
        300,
      );
    },

    // --- Viewport state ---
    viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },

    pan: (dx: number, dy: number): void => {
      cancelViewportAnimation();
      set((state) => ({
        viewport: {
          ...state.viewport,
          offsetX: state.viewport.offsetX + dx,
          offsetY: state.viewport.offsetY + dy,
        },
      }));
    },

    zoom: (factor: number, center: Point): void => {
      cancelViewportAnimation();
      set((state) => ({
        viewport: zoomAtPoint(state.viewport, factor, center),
      }));
    },
});
