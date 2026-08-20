/**
 * How lines attach to objects — anchors, waypoints and pull-to-connect.
 */

import type { StateCreator } from 'zustand';
import type { AnchorRef, LineObject, Point } from '@/types/diagram';
import { computeOptimalExitSide, getAnchorPoints } from '@/utils/anchor';
import type { AnchorPosition } from '@/utils/anchor';
import { getConnectionBounds } from '@/utils/bounds-utils';
import type { DiagramStore } from './store-types';

export interface AnchoringSlice {
  // Anchor management
  updateLineAnchors: (lineId: string, anchors: { sourceAnchor?: AnchorRef | null; targetAnchor?: AnchorRef | null }) => void;
  recomputeAnchoredEndpoints: (movedObjectId: string) => void;

  // Waypoint and anchor position management
  updateLineWaypoints: (lineId: string, waypoints: Point[] | null) => void;
  updateLineAnchorPosition: (lineId: string, endpoint: 'source' | 'target', position: AnchorPosition) => void;
  updateLineLabelOffset: (lineId: string, offset: Point | null) => void;
  updateLineCustomLabel: (lineId: string, label: string | null) => void;

  // Pull-to-connect state
  pullConnectState: { sourceObjectId: string; sourceAnchorPoint: Point; sourceAnchorPosition: AnchorPosition } | null;
  setPullConnectState: (state: { sourceObjectId: string; sourceAnchorPoint: Point; sourceAnchorPosition: AnchorPosition } | null) => void;
}

export const createAnchoringSlice: StateCreator<DiagramStore, [], [], AnchoringSlice> = (set, get) => ({
    // --- Anchor management ---

    updateLineAnchors: (lineId: string, anchors: { sourceAnchor?: AnchorRef | null; targetAnchor?: AnchorRef | null }): void => {
      const existing = get().canvasObjects.get(lineId);
      if (!existing || existing.objectType !== 'line') return;
      get().pushHistory();

      const updated: LineObject = { ...existing };
      if ('sourceAnchor' in anchors) {
        updated.sourceAnchor = anchors.sourceAnchor ?? null;
      }
      if ('targetAnchor' in anchors) {
        updated.targetAnchor = anchors.targetAnchor ?? null;
      }

      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(lineId, updated);
        return { canvasObjects: next };
      });
    },

    recomputeAnchoredEndpoints: (movedObjectId: string): void => {
      const { canvasObjects } = get();
      const movedObj = canvasObjects.get(movedObjectId);
      if (!movedObj) return;

      const movedBounds = getConnectionBounds(movedObj);
      const updates = new Map<string, LineObject>();

      for (const obj of canvasObjects.values()) {
        if (obj.objectType !== 'line') continue;
        const line = obj as LineObject;
        const updatedLine = { ...line };
        let updated = false;

        // Re-evaluate source anchor position if the moved object is the source
        if (line.sourceAnchor?.objectId === movedObjectId) {
          // Use the center of the other object (or the free endpoint) as reference
          let otherPt = line.end;
          if (line.targetAnchor) {
            const targetObj = canvasObjects.get(line.targetAnchor.objectId);
            if (targetObj) {
              const tb = getConnectionBounds(targetObj);
              otherPt = { x: tb.x + tb.width / 2, y: tb.y + tb.height / 2 };
            }
          }
          const bestPos = computeOptimalExitSide(movedBounds, otherPt, line.sourceAnchor.anchorPosition);
          updatedLine.sourceAnchor = { ...line.sourceAnchor, anchorPosition: bestPos };
          updatedLine.start = getAnchorPoints(movedBounds)[bestPos];
          updated = true;
        }

        // Re-evaluate target anchor position if the moved object is the target
        if (line.targetAnchor?.objectId === movedObjectId) {
          // Use the center of the other object (or the free endpoint) as reference
          let otherPt = updatedLine.start;
          if (line.sourceAnchor) {
            const sourceObj = canvasObjects.get(line.sourceAnchor.objectId);
            if (sourceObj && line.sourceAnchor.objectId !== movedObjectId) {
              const sb = getConnectionBounds(sourceObj);
              otherPt = { x: sb.x + sb.width / 2, y: sb.y + sb.height / 2 };
            }
          }
          const bestPos = computeOptimalExitSide(movedBounds, otherPt, line.targetAnchor.anchorPosition);
          updatedLine.targetAnchor = { ...line.targetAnchor, anchorPosition: bestPos };
          updatedLine.end = getAnchorPoints(movedBounds)[bestPos];
          updated = true;
        }

        if (updated) {
          // Also re-evaluate the non-moved end's anchor since relative geometry changed
          if (updatedLine.sourceAnchor && updatedLine.sourceAnchor.objectId !== movedObjectId) {
            const sourceObj = canvasObjects.get(updatedLine.sourceAnchor.objectId);
            if (sourceObj) {
              const sourceBounds = getConnectionBounds(sourceObj);
              const movedCenter = { x: movedBounds.x + movedBounds.width / 2, y: movedBounds.y + movedBounds.height / 2 };
              const bestSourcePos = computeOptimalExitSide(sourceBounds, movedCenter, updatedLine.sourceAnchor.anchorPosition);
              updatedLine.sourceAnchor = { ...updatedLine.sourceAnchor, anchorPosition: bestSourcePos };
              updatedLine.start = getAnchorPoints(sourceBounds)[bestSourcePos];
            }
          }
          if (updatedLine.targetAnchor && updatedLine.targetAnchor.objectId !== movedObjectId) {
            const targetObj = canvasObjects.get(updatedLine.targetAnchor.objectId);
            if (targetObj) {
              const targetBounds = getConnectionBounds(targetObj);
              const movedCenter = { x: movedBounds.x + movedBounds.width / 2, y: movedBounds.y + movedBounds.height / 2 };
              const bestTargetPos = computeOptimalExitSide(targetBounds, movedCenter, updatedLine.targetAnchor.anchorPosition);
              updatedLine.targetAnchor = { ...updatedLine.targetAnchor, anchorPosition: bestTargetPos };
              updatedLine.end = getAnchorPoints(targetBounds)[bestTargetPos];
            }
          }
          updatedLine.waypoints = null;
          updates.set(line.id, updatedLine as LineObject);
        }
      }

      if (updates.size === 0) return;

      set((state) => {
        const next = new Map(state.canvasObjects);
        for (const [id, updated] of updates) {
          next.set(id, updated);
        }
        return { canvasObjects: next };
      });
    },

    // --- Waypoint and anchor position management ---

    updateLineWaypoints: (lineId: string, waypoints: Point[] | null): void => {
      const existing = get().canvasObjects.get(lineId);
      if (!existing || existing.objectType !== 'line') return;
      get().pushHistory();

      const updated: LineObject = { ...existing, waypoints };

      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(lineId, updated);
        return { canvasObjects: next };
      });
    },

    updateLineAnchorPosition: (lineId: string, endpoint: 'source' | 'target', position: AnchorPosition): void => {
      const existing = get().canvasObjects.get(lineId);
      if (!existing || existing.objectType !== 'line') return;

      const anchorKey = endpoint === 'source' ? 'sourceAnchor' : 'targetAnchor';
      const currentAnchor = existing[anchorKey];
      if (!currentAnchor) return; // No anchor to update

      const updated: LineObject = {
        ...existing,
        [anchorKey]: { ...currentAnchor, anchorPosition: position },
      };

      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(lineId, updated);
        return { canvasObjects: next };
      });
    },

    updateLineLabelOffset: (lineId: string, offset: Point | null): void => {
      const existing = get().canvasObjects.get(lineId);
      if (!existing || existing.objectType !== 'line') return;

      const updated: LineObject = { ...existing, labelOffset: offset };
      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(lineId, updated);
        return { canvasObjects: next };
      });
    },

    updateLineCustomLabel: (lineId: string, label: string | null): void => {
      const existing = get().canvasObjects.get(lineId);
      if (!existing || existing.objectType !== 'line') return;
      get().pushHistory();

      const updated: LineObject = { ...existing, customLabel: label };
      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(lineId, updated);
        return { canvasObjects: next };
      });
    },

    // --- Pull-to-connect state ---

    pullConnectState: null as { sourceObjectId: string; sourceAnchorPoint: Point; sourceAnchorPosition: AnchorPosition } | null,

    setPullConnectState: (state: { sourceObjectId: string; sourceAnchorPoint: Point; sourceAnchorPosition: AnchorPosition } | null): void => {
      set({ pullConnectState: state });
    },
});
