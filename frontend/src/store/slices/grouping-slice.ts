/**
 * Grouping canvas objects together.
 */

import type { StateCreator } from 'zustand';
import type { CanvasObject, ObjectGroup } from '@/types/diagram';
import { v4 as uuidv4 } from 'uuid';
import type { DiagramStore } from './store-types';

export interface GroupingSlice {
  // Grouping
  objectGroups: Map<string, ObjectGroup>;
  groupSelectedObjects: () => string | null;
  ungroupObjects: (groupId: string) => void;
}

export const createGroupingSlice: StateCreator<DiagramStore, [], [], GroupingSlice> = (set, get) => ({
    // --- Grouping actions ---
    objectGroups: new Map<string, ObjectGroup>(),


    groupSelectedObjects: (): string | null => {
      const { selectedObjectIds, canvasObjects, objectGroups } = get();
      // Require at least 2 selected objects
      if (selectedObjectIds.size < 2) return null;

      // Verify all selected IDs exist
      for (const id of selectedObjectIds) {
        if (!canvasObjects.has(id)) return null;
      }

      get().pushHistory();

      const groupId = uuidv4();
      // Auto-generate group name
      const groupNumber = objectGroups.size + 1;
      const groupName = `Group ${groupNumber}`;
      const memberIds = Array.from(selectedObjectIds);

      set((state) => {
        const nextObjects = new Map(state.canvasObjects);
        const nextGroups = new Map(state.objectGroups);

        // Remove members from any existing groups first
        for (const memberId of memberIds) {
          const obj = nextObjects.get(memberId);
          if (obj && obj.groupId) {
            const oldGroup = nextGroups.get(obj.groupId);
            if (oldGroup) {
              const remaining = oldGroup.memberIds.filter((mid) => mid !== memberId);
              if (remaining.length < 2) {
                // Auto-dissolve old group
                for (const rid of remaining) {
                  const rObj = nextObjects.get(rid);
                  if (rObj) {
                    nextObjects.set(rid, { ...rObj, groupId: undefined } as CanvasObject);
                  }
                }
                nextGroups.delete(obj.groupId);
              } else {
                nextGroups.set(obj.groupId, { ...oldGroup, memberIds: remaining });
              }
            }
          }
        }

        // Set groupId on all members
        for (const memberId of memberIds) {
          const obj = nextObjects.get(memberId);
          if (obj) {
            nextObjects.set(memberId, { ...obj, groupId: groupId } as CanvasObject);
          }
        }

        // Create the new group
        const newGroup: ObjectGroup = { id: groupId, name: groupName, memberIds };
        nextGroups.set(groupId, newGroup);

        return { canvasObjects: nextObjects, objectGroups: nextGroups };
      });

      return groupId;
    },

    ungroupObjects: (groupId: string): void => {
      const { objectGroups } = get();
      const group = objectGroups.get(groupId);
      if (!group) return;
      get().pushHistory();

      set((state) => {
        const nextObjects = new Map(state.canvasObjects);
        const nextGroups = new Map(state.objectGroups);

        // Clear groupId on all members
        for (const memberId of group.memberIds) {
          const obj = nextObjects.get(memberId);
          if (obj) {
            nextObjects.set(memberId, { ...obj, groupId: undefined } as CanvasObject);
          }
        }

        // Remove the group
        nextGroups.delete(groupId);

        return { canvasObjects: nextObjects, objectGroups: nextGroups };
      });
    },
});
