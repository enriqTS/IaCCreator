/**
 * Canvas Slice — CanvasObject CRUD, selection, z-order, and grouping logic.
 *
 * This file defines the public contract (CanvasSlice interface) for the canvas
 * concerns of the diagram store. The actual implementation will be extracted
 * from diagram-store.ts in a subsequent pass (task 10.6).
 *
 * Requirements: 7.1, 7.8
 */

import type { StateCreator } from 'zustand';
import type {
  CanvasObject,
  CanvasObjectCreationPayload,
  Point,
  ObjectGroup,
  Rect,
  ArchitectureBlockVisualConfig,
  LineVisualConfig,
  GeometricVisualConfig,
  TextVisualConfig,
  UMLVisualConfig,
  AnchorRef,
} from '@/types/diagram';
import type { AnchorPosition } from '@/utils/anchor';

// ---------------------------------------------------------------------------
// Slice interface
// ---------------------------------------------------------------------------

export interface CanvasSlice {
  // --- State ---
  canvasObjects: Map<string, CanvasObject>;
  selectedObjectIds: Set<string>;
  objectGroups: Map<string, ObjectGroup>;
  clipboard: CanvasObject[];
  editingTextId: string | null;
  pullConnectState: {
    sourceObjectId: string;
    sourceAnchorPoint: Point;
    sourceAnchorPosition: AnchorPosition;
  } | null;

  // --- CRUD ---
  addCanvasObject: (obj: CanvasObjectCreationPayload) => string;
  updateCanvasObject: (id: string, updates: Partial<CanvasObject>) => void;
  removeCanvasObject: (id: string) => void;
  updateVisualConfig: (
    id: string,
    config: Partial<
      | ArchitectureBlockVisualConfig
      | LineVisualConfig
      | GeometricVisualConfig
      | TextVisualConfig
      | UMLVisualConfig
    >,
  ) => void;
  updateObjectBounds: (id: string, bounds: { width?: number; height?: number }) => void;
  updateLineEndpoint: (id: string, endpoint: 'start' | 'end', position: Point) => void;

  // --- Selection ---
  selectObject: (id: string | null) => void;
  toggleObjectSelection: (id: string) => void;
  selectObjectsByRect: (rect: Rect) => void;
  clearSelection: () => void;
  selectAllObjects: () => void;

  // --- Z-order ---
  bringToFront: (id: string) => void;
  sendToBack: (id: string) => void;
  bringForward: (id: string) => void;
  sendBackward: (id: string) => void;

  // --- Grouping ---
  groupSelectedObjects: () => string | null;
  ungroupObjects: (groupId: string) => void;

  // --- Clipboard ---
  copySelectedObjects: () => void;
  pasteObjects: (position: Point) => void;
  duplicateSelectedObjects: () => void;

  // --- Lock ---
  toggleLockObjects: (ids: Set<string>) => void;

  // --- Movement ---
  moveSelectedObjects: (dx: number, dy: number) => void;

  // --- Text editing ---
  setEditingTextId: (id: string | null) => void;
  updateTextContent: (id: string, content: string) => void;

  // --- Anchor management ---
  updateLineAnchors: (
    lineId: string,
    anchors: { sourceAnchor?: AnchorRef | null; targetAnchor?: AnchorRef | null },
  ) => void;
  recomputeAnchoredEndpoints: (movedObjectId: string) => void;
  updateLineWaypoints: (lineId: string, waypoints: Point[] | null) => void;
  updateLineAnchorPosition: (
    lineId: string,
    endpoint: 'source' | 'target',
    position: AnchorPosition,
  ) => void;

  // --- Pull-to-connect ---
  setPullConnectState: (
    state: {
      sourceObjectId: string;
      sourceAnchorPoint: Point;
      sourceAnchorPosition: AnchorPosition;
    } | null,
  ) => void;

  // --- Fit to screen ---
  fitToScreen: (containerRect: { width: number; height: number }) => void;
}

// ---------------------------------------------------------------------------
// Slice creator (placeholder)
// ---------------------------------------------------------------------------

/**
 * Placeholder creator — actual implementation will be extracted from
 * diagram-store.ts during the composition pass (task 10.6).
 *
 * The type signature below establishes the contract that the composition
 * point will use when wiring slices together.
 */
export type CreateCanvasSlice = StateCreator<
  CanvasSlice,
  [],
  [],
  CanvasSlice
>;
