/**
 * Viewport Slice — Pan, zoom, and viewport reset logic.
 *
 * This file defines the public contract (ViewportSlice interface) for the
 * viewport concerns of the diagram store. The actual implementation will be
 * extracted from diagram-store.ts in a subsequent pass (task 10.6).
 *
 * Requirements: 7.1, 7.6
 */

import type { StateCreator } from 'zustand';
import type { Viewport, Point } from '@/types/diagram';

export interface ViewportSlice {
  viewport: Viewport;
  setViewport: (viewport: Viewport) => void;
  panViewport: (dx: number, dy: number) => void;
  zoomViewport: (delta: number, center: Point) => void;
  resetViewport: () => void;
}

export type CreateViewportSlice = StateCreator<ViewportSlice, [], [], ViewportSlice>;
