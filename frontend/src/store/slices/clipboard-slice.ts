/**
 * Copying, pasting and duplicating canvas objects.
 */

import type { StateCreator } from 'zustand';
import type { ArchitectureBlock, CanvasObject, LineObject, Point } from '@/types/diagram';
import { v4 as uuidv4 } from 'uuid';
import type { DiagramStore } from './store-types';

export interface ClipboardSlice {
  // Clipboard
  clipboard: CanvasObject[];
  copySelectedObjects: () => void;
  pasteObjects: (position: Point) => void;

  // Duplicate
  duplicateSelectedObjects: () => void;
}

export const createClipboardSlice: StateCreator<DiagramStore, [], [], ClipboardSlice> = (set, get) => ({
    // --- Clipboard actions ---
    clipboard: [] as CanvasObject[],


    copySelectedObjects: (): void => {
      const { selectedObjectIds, canvasObjects } = get();
      if (selectedObjectIds.size === 0) return;

      const copied: CanvasObject[] = [];
      for (const id of selectedObjectIds) {
        const obj = canvasObjects.get(id);
        if (obj) {
          copied.push({ ...obj });
        }
      }
      set({ clipboard: copied });
    },

    pasteObjects: (position: Point): void => {
      const { clipboard, canvasObjects } = get();
      if (clipboard.length === 0) return;

      get().pushHistory();

      // Compute centroid of copied objects
      let sumX = 0;
      let sumY = 0;
      for (const obj of clipboard) {
        if (obj.objectType === 'line') {
          sumX += (obj.start.x + obj.end.x) / 2;
          sumY += (obj.start.y + obj.end.y) / 2;
        } else {
          sumX += obj.position.x;
          sumY += obj.position.y;
        }
      }
      const centroidX = sumX / clipboard.length;
      const centroidY = sumY / clipboard.length;

      // Compute max zIndex
      let maxZ = -1;
      for (const existing of canvasObjects.values()) {
        if (existing.zIndex > maxZ) maxZ = existing.zIndex;
      }

      const offsetX = position.x - centroidX;
      const offsetY = position.y - centroidY;

      // Build ID mapping (oldId → newId) for all objects in clipboard
      const idMap = new Map<string, string>();
      for (const obj of clipboard) {
        idMap.set(obj.id, uuidv4());
      }

      const newIds = new Set<string>();
      const nextObjects = new Map(canvasObjects);

      // First pass: paste non-line objects
      for (const obj of clipboard) {
        if (obj.objectType === 'line') continue;

        const newId = idMap.get(obj.id)!;
        newIds.add(newId);
        maxZ++;

        if (obj.objectType === 'architecture-block') {
          const pasted: ArchitectureBlock = {
            ...obj,
            id: newId,
            zIndex: maxZ,
            groupId: undefined,
            position: { x: obj.position.x + offsetX, y: obj.position.y + offsetY },
          };
          nextObjects.set(newId, pasted);
        } else {
          // geometric / text / uml
          const pasted: CanvasObject = {
            ...obj,
            id: newId,
            zIndex: maxZ,
            groupId: undefined,
            position: { x: obj.position.x + offsetX, y: obj.position.y + offsetY },
          } as CanvasObject;
          nextObjects.set(newId, pasted);
        }
      }

      // Second pass: paste line objects with remapped anchors
      for (const obj of clipboard) {
        if (obj.objectType !== 'line') continue;

        const newId = idMap.get(obj.id)!;
        newIds.add(newId);
        maxZ++;

        // Remap anchors: if the referenced object was in the clipboard, point to its new ID
        let newSourceAnchor = obj.sourceAnchor;
        if (newSourceAnchor) {
          const mappedId = idMap.get(newSourceAnchor.objectId);
          if (mappedId) {
            newSourceAnchor = { ...newSourceAnchor, objectId: mappedId };
          } else {
            newSourceAnchor = null; // Referenced object not in clipboard — detach
          }
        }

        let newTargetAnchor = obj.targetAnchor;
        if (newTargetAnchor) {
          const mappedId = idMap.get(newTargetAnchor.objectId);
          if (mappedId) {
            newTargetAnchor = { ...newTargetAnchor, objectId: mappedId };
          } else {
            newTargetAnchor = null; // Referenced object not in clipboard — detach
          }
        }

        const pasted: LineObject = {
          ...obj,
          id: newId,
          zIndex: maxZ,
          groupId: undefined,
          start: { x: obj.start.x + offsetX, y: obj.start.y + offsetY },
          end: { x: obj.end.x + offsetX, y: obj.end.y + offsetY },
          sourceAnchor: newSourceAnchor,
          targetAnchor: newTargetAnchor,
          waypoints: null, // Clear waypoints — route will be recomputed
        };
        nextObjects.set(newId, pasted);
      }

      set({ canvasObjects: nextObjects, selectedObjectIds: newIds });
    },

    // --- Duplicate ---

    duplicateSelectedObjects: (): void => {
      const { selectedObjectIds, canvasObjects } = get();
      if (selectedObjectIds.size === 0) return;

      get().pushHistory();

      let maxZ = -1;
      for (const existing of canvasObjects.values()) {
        if (existing.zIndex > maxZ) maxZ = existing.zIndex;
      }

      // Build ID mapping (oldId → newId) for all selected objects
      const idMap = new Map<string, string>();
      for (const id of selectedObjectIds) {
        idMap.set(id, uuidv4());
      }

      const newIds = new Set<string>();
      const nextObjects = new Map(canvasObjects);

      // First pass: duplicate non-line objects
      for (const id of selectedObjectIds) {
        const obj = canvasObjects.get(id);
        if (!obj || obj.objectType === 'line') continue;

        const newId = idMap.get(id)!;
        newIds.add(newId);
        maxZ++;

        if (obj.objectType === 'architecture-block') {
          const dup: ArchitectureBlock = {
            ...obj,
            id: newId,
            zIndex: maxZ,
            groupId: undefined,
            position: { x: obj.position.x + 20, y: obj.position.y + 20 },
          };
          nextObjects.set(newId, dup);
        } else {
          const dup: CanvasObject = {
            ...obj,
            id: newId,
            zIndex: maxZ,
            groupId: undefined,
            position: { x: obj.position.x + 20, y: obj.position.y + 20 },
          } as CanvasObject;
          nextObjects.set(newId, dup);
        }
      }

      // Second pass: duplicate line objects with remapped anchors
      for (const id of selectedObjectIds) {
        const obj = canvasObjects.get(id);
        if (!obj || obj.objectType !== 'line') continue;

        const newId = idMap.get(id)!;
        newIds.add(newId);
        maxZ++;

        // Remap anchors: if the referenced object was selected, point to its new ID
        let newSourceAnchor = obj.sourceAnchor;
        if (newSourceAnchor) {
          const mappedId = idMap.get(newSourceAnchor.objectId);
          if (mappedId) {
            newSourceAnchor = { ...newSourceAnchor, objectId: mappedId };
          } else {
            newSourceAnchor = null; // Referenced object not selected — detach
          }
        }

        let newTargetAnchor = obj.targetAnchor;
        if (newTargetAnchor) {
          const mappedId = idMap.get(newTargetAnchor.objectId);
          if (mappedId) {
            newTargetAnchor = { ...newTargetAnchor, objectId: mappedId };
          } else {
            newTargetAnchor = null; // Referenced object not selected — detach
          }
        }

        const dup: LineObject = {
          ...obj,
          id: newId,
          zIndex: maxZ,
          groupId: undefined,
          start: { x: obj.start.x + 20, y: obj.start.y + 20 },
          end: { x: obj.end.x + 20, y: obj.end.y + 20 },
          sourceAnchor: newSourceAnchor,
          targetAnchor: newTargetAnchor,
          waypoints: null, // Clear waypoints — route will be recomputed
        };
        nextObjects.set(newId, dup);
      }

      set({ canvasObjects: nextObjects, selectedObjectIds: newIds });
    },
});
