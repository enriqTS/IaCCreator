/**
 * Canvas objects — creation, selection, movement and text editing.
 */

import type { StateCreator } from 'zustand';
import type { ArchitectureBlockVisualConfig, CanvasObject, CanvasObjectCreationPayload, ContainerVisualConfig, GeometricVisualConfig, LineObject, LineVisualConfig, Point, Rect, TextVisualConfig, UMLVisualConfig } from '@/types/diagram';
import { MIN_OBJECT_HEIGHT, MIN_OBJECT_WIDTH, getObjectBounds } from '@/types/diagram';
import { apiClient } from '@/utils/api-client';
import { useToastStore } from '@/store/toast-store';
import { v4 as uuidv4 } from 'uuid';
import type { DiagramStore } from './store-types';

let resourceInitializationQueue = Promise.resolve();

export interface CanvasSlice {
  // Canvas object state
  canvasObjects: Map<string, CanvasObject>;
  selectedObjectIds: Set<string>;
  addCanvasObject: (obj: CanvasObjectCreationPayload) => string;
  updateCanvasObject: (id: string, updates: Partial<CanvasObject>) => void;
  removeCanvasObject: (id: string) => void;
  removeMultipleCanvasObjects: (ids: Set<string>) => void;
  selectObject: (id: string | null) => void;
  toggleObjectSelection: (id: string) => void;
  selectObjectsByRect: (rect: Rect) => void;
  clearSelection: () => void;
  updateVisualConfig: (id: string, config: Partial<ArchitectureBlockVisualConfig | ContainerVisualConfig | LineVisualConfig | GeometricVisualConfig | TextVisualConfig | UMLVisualConfig>) => void;
  updateObjectBounds: (id: string, bounds: { width?: number; height?: number }) => void;
  updateLineEndpoint: (id: string, endpoint: 'start' | 'end', position: Point) => void;

  // Lock
  toggleLockObjects: (ids: Set<string>) => void;

  // Select all
  selectAllObjects: () => void;

  // Multi-object move
  moveSelectedObjects: (dx: number, dy: number) => void;

  // Text editing
  editingTextId: string | null;
  setEditingTextId: (id: string | null) => void;
  updateTextContent: (id: string, content: string) => void;
}

export const createCanvasSlice: StateCreator<DiagramStore, [], [], CanvasSlice> = (set, get) => ({
    // --- Canvas object state ---
    canvasObjects: new Map<string, CanvasObject>(),
    selectedObjectIds: new Set<string>(),

    addCanvasObject: (obj: CanvasObjectCreationPayload): string => {
      get().pushHistory();
      const id = uuidv4();
      // Assign zIndex as maxZIndex + 1
      const { canvasObjects } = get();
      let maxZ = -1;
      for (const existing of canvasObjects.values()) {
        if (existing.zIndex > maxZ) maxZ = existing.zIndex;
      }
      let canvasObject = { ...obj, id, zIndex: maxZ + 1 } as CanvasObject;

      if (canvasObject.objectType === 'architecture-block') {
        const explicitName = (obj as { name?: string }).name;
        canvasObject = {
          ...canvasObject,
          name: explicitName || `${canvasObject.serviceType}-${id.slice(0, 8)}`,
          terraformVariables: {
            ...(obj as { terraformVariables?: Record<string, string | number | boolean> }).terraformVariables,
          },
        };
        if (!explicitName) {
          const temporaryName = canvasObject.name;
          const serviceType = canvasObject.serviceType;
          resourceInitializationQueue = resourceInitializationQueue.then(async () => {
            const existingNames = Array.from(get().canvasObjects.values())
              .filter((item) => item.id !== id)
              .map((item) => item.name);
            const result = await apiClient.initializeResource(serviceType, existingNames);
            if (!result.ok) {
              useToastStore.getState().addToast(result.error.message, 'error');
              return;
            }
            const current = get().canvasObjects.get(id);
            if (!current || current.objectType !== 'architecture-block') return;
            get().updateCanvasObject(id, {
              name: current.name === temporaryName ? result.data.name : current.name,
              defaultName: result.data.name,
              config: { ...result.data.config, ...current.config },
              terraformVariables: {
                ...result.data.terraform_variables,
                ...current.terraformVariables,
              },
            } as Partial<CanvasObject>);
          });
        }
      }

      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(id, canvasObject);
        return { canvasObjects: next };
      });

      return id;
    },

    updateCanvasObject: (id: string, updates: Partial<CanvasObject>): void => {
      const existing = get().canvasObjects.get(id);
      if (!existing) return;

      const merged = { ...existing, ...updates, id: existing.id, objectType: existing.objectType } as CanvasObject;

      // Enforce minimum dimension clamping for objects with width/height
      if (merged.objectType === 'architecture-block') {
        merged.visualConfig = {
          ...merged.visualConfig,
          width: Math.max(merged.visualConfig.width, MIN_OBJECT_WIDTH),
          height: Math.max(merged.visualConfig.height, MIN_OBJECT_HEIGHT),
        };
      } else if (merged.objectType === 'semantic-container') {
        merged.visualConfig = {
          ...merged.visualConfig,
          width: Math.max(merged.visualConfig.width, MIN_OBJECT_WIDTH),
          height: Math.max(merged.visualConfig.height, MIN_OBJECT_HEIGHT),
        };
      } else if (merged.objectType === 'geometric') {
        merged.visualConfig = {
          ...merged.visualConfig,
          width: Math.max(merged.visualConfig.width, MIN_OBJECT_WIDTH),
          height: Math.max(merged.visualConfig.height, MIN_OBJECT_HEIGHT),
        };
      }

      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(id, merged);
        return { canvasObjects: next };
      });
    },

    removeCanvasObject: (id: string): void => {
      if (!get().canvasObjects.has(id)) return;
      get().pushHistory();

      set((state) => {
        const next = new Map(state.canvasObjects);
        const obj = state.canvasObjects.get(id)!;
        next.delete(id);

        const nextConnectors = new Map(state.connectors);
        for (const [cid, conn] of state.connectors) {
          if (conn.sourceId === id || conn.targetId === id) nextConnectors.delete(cid);
        }

        const deletedParentId = 'parentContainerId' in obj ? obj.parentContainerId : undefined;
        for (const [childId, child] of next) {
          if ('parentContainerId' in child && child.parentContainerId === id) {
            next.set(childId, { ...child, parentContainerId: deletedParentId } as CanvasObject);
          }
        }

        // Clear selection if deleting the selected object
        const nextSelectedObjectIds = new Set(state.selectedObjectIds);
        nextSelectedObjectIds.delete(id);

        // Handle group membership: remove from group, auto-dissolve if < 2 members
        const nextGroups = new Map(state.objectGroups);
        if (obj.groupId) {
          const group = nextGroups.get(obj.groupId);
          if (group) {
            const updatedMembers = group.memberIds.filter((mid) => mid !== id);
            if (updatedMembers.length < 2) {
              // Auto-dissolve: clear groupId on remaining members
              for (const memberId of updatedMembers) {
                const member = next.get(memberId);
                if (member) {
                  next.set(memberId, { ...member, groupId: undefined } as CanvasObject);
                }
              }
              nextGroups.delete(obj.groupId);
            } else {
              nextGroups.set(obj.groupId, { ...group, memberIds: updatedMembers });
            }
          }
        }

        // Detach anchors on lines referencing the deleted object (nullify, don't delete lines)
        for (const [lineId, lineObj] of next) {
          if (lineObj.objectType !== 'line') continue;
          const line = lineObj as LineObject;
          let needsUpdate = false;
          let newSourceAnchor = line.sourceAnchor;
          let newTargetAnchor = line.targetAnchor;

          if (line.sourceAnchor?.objectId === id) {
            newSourceAnchor = null;
            needsUpdate = true;
          }
          if (line.targetAnchor?.objectId === id) {
            newTargetAnchor = null;
            needsUpdate = true;
          }
          if (needsUpdate) {
            next.set(lineId, { ...line, sourceAnchor: newSourceAnchor, targetAnchor: newTargetAnchor });
          }
        }

        return { canvasObjects: next, connectors: nextConnectors, selectedObjectIds: nextSelectedObjectIds, objectGroups: nextGroups };
      });
    },

    removeMultipleCanvasObjects: (ids: Set<string>): void => {
      if (ids.size === 0) return;

      // Verify at least one exists
      const { canvasObjects } = get();
      let anyExists = false;
      for (const id of ids) {
        if (canvasObjects.has(id)) { anyExists = true; break; }
      }
      if (!anyExists) return;

      get().pushHistory();

      set((state) => {
        const next = new Map(state.canvasObjects);
        const nextConnectors = new Map(state.connectors);
        const nextGroups = new Map(state.objectGroups);
        const nextSelectedObjectIds = new Set(state.selectedObjectIds);

        for (const id of ids) {
          const obj = next.get(id);
          if (!obj) continue;

          next.delete(id);
          nextSelectedObjectIds.delete(id);

          for (const [cid, conn] of nextConnectors) {
            if (conn.sourceId === id || conn.targetId === id) nextConnectors.delete(cid);
          }

          // Handle group membership
          if (obj.groupId) {
            const group = nextGroups.get(obj.groupId);
            if (group) {
              const updatedMembers = group.memberIds.filter((mid) => !ids.has(mid));
              if (updatedMembers.length < 2) {
                for (const memberId of updatedMembers) {
                  const member = next.get(memberId);
                  if (member) {
                    next.set(memberId, { ...member, groupId: undefined } as CanvasObject);
                  }
                }
                nextGroups.delete(obj.groupId);
              } else {
                nextGroups.set(obj.groupId, { ...group, memberIds: updatedMembers });
              }
            }
          }
        }

        for (const [childId, child] of next) {
          if (!('parentContainerId' in child) || !child.parentContainerId || !ids.has(child.parentContainerId)) continue;
          let parentId: string | undefined = child.parentContainerId;
          const visited = new Set<string>();
          while (parentId && ids.has(parentId) && !visited.has(parentId)) {
            visited.add(parentId);
            const parent = state.canvasObjects.get(parentId);
            parentId = parent && 'parentContainerId' in parent ? parent.parentContainerId : undefined;
          }
          next.set(childId, { ...child, parentContainerId: parentId } as CanvasObject);
        }

        // Detach anchors on remaining lines that reference any deleted object
        for (const [lineId, lineObj] of next) {
          if (lineObj.objectType !== 'line') continue;
          const line = lineObj as LineObject;
          let needsUpdate = false;
          let newSourceAnchor = line.sourceAnchor;
          let newTargetAnchor = line.targetAnchor;

          if (newSourceAnchor && ids.has(newSourceAnchor.objectId)) {
            newSourceAnchor = null;
            needsUpdate = true;
          }
          if (newTargetAnchor && ids.has(newTargetAnchor.objectId)) {
            newTargetAnchor = null;
            needsUpdate = true;
          }
          if (needsUpdate) {
            next.set(lineId, { ...line, sourceAnchor: newSourceAnchor, targetAnchor: newTargetAnchor });
          }
        }

        return { canvasObjects: next, connectors: nextConnectors, selectedObjectIds: nextSelectedObjectIds, objectGroups: nextGroups };
      });
    },

    selectObject: (id: string | null): void => {
      if (!id) {
        set({ selectedObjectIds: new Set() });
        return;
      }
      const { canvasObjects, objectGroups } = get();
      const obj = canvasObjects.get(id);
      if (obj?.groupId) {
        const group = objectGroups.get(obj.groupId);
        if (group) {
          set({ selectedObjectIds: new Set(group.memberIds) });
          return;
        }
      }
      set({ selectedObjectIds: new Set([id]) });
    },

    toggleObjectSelection: (id: string): void => {
      set((state) => {
        const next = new Set(state.selectedObjectIds);
        if (next.has(id)) {
          next.delete(id);
        } else {
          next.add(id);
        }
        return { selectedObjectIds: next };
      });
    },

    selectObjectsByRect: (rect: Rect): void => {
      const { canvasObjects } = get();
      const selected = new Set<string>();
      for (const obj of canvasObjects.values()) {
        const bounds = getObjectBounds(obj);
        // Check AABB intersection
        if (
          bounds.x + bounds.width > rect.x &&
          bounds.x < rect.x + rect.width &&
          bounds.y + bounds.height > rect.y &&
          bounds.y < rect.y + rect.height
        ) {
          selected.add(obj.id);
        }
      }
      set({ selectedObjectIds: selected });
    },

    clearSelection: (): void => {
      set({ selectedObjectIds: new Set() });
    },

    updateVisualConfig: (id: string, config: Partial<ArchitectureBlockVisualConfig | LineVisualConfig | GeometricVisualConfig | TextVisualConfig | UMLVisualConfig>): void => {
      const existing = get().canvasObjects.get(id);
      if (!existing) return;
      get().pushHistory();

      const mergedConfig = { ...existing.visualConfig, ...config };

      // Enforce minimum dimensions for object types with width/height
      if (existing.objectType === 'architecture-block' || existing.objectType === 'geometric' || existing.objectType === 'text' || existing.objectType === 'uml') {
        const withDims = mergedConfig as { width: number; height: number };
        withDims.width = Math.max(withDims.width, MIN_OBJECT_WIDTH);
        withDims.height = Math.max(withDims.height, MIN_OBJECT_HEIGHT);
      }

      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(id, { ...existing, visualConfig: mergedConfig } as CanvasObject);
        return { canvasObjects: next };
      });
    },

    updateObjectBounds: (id: string, bounds: { width?: number; height?: number }): void => {
      const existing = get().canvasObjects.get(id);
      if (!existing) return;
      if (existing.objectType === 'line') return; // Lines don't have width/height bounds

      const currentConfig = existing.visualConfig as { width: number; height: number };
      const newWidth = Math.max(bounds.width ?? currentConfig.width, MIN_OBJECT_WIDTH);
      const newHeight = Math.max(bounds.height ?? currentConfig.height, MIN_OBJECT_HEIGHT);

      const mergedConfig = { ...existing.visualConfig, width: newWidth, height: newHeight };

      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(id, { ...existing, visualConfig: mergedConfig } as CanvasObject);
        return { canvasObjects: next };
      });
    },

    updateLineEndpoint: (id: string, endpoint: 'start' | 'end', position: Point): void => {
      const existing = get().canvasObjects.get(id);
      if (!existing || existing.objectType !== 'line') return;

      const updated = { ...existing, [endpoint]: { ...position }, waypoints: null };

      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(id, updated);
        return { canvasObjects: next };
      });
    },

    // --- Lock/Unlock ---

    toggleLockObjects: (ids: Set<string>): void => {
      const { canvasObjects } = get();
      if (ids.size === 0) return;

      // Determine if any are unlocked
      let anyUnlocked = false;
      for (const id of ids) {
        const obj = canvasObjects.get(id);
        if (obj && !obj.locked) {
          anyUnlocked = true;
          break;
        }
      }

      get().pushHistory();

      const newLocked = anyUnlocked; // if any unlocked, lock all; if all locked, unlock all

      set((state) => {
        const next = new Map(state.canvasObjects);
        for (const id of ids) {
          const obj = next.get(id);
          if (obj) {
            next.set(id, { ...obj, locked: newLocked } as CanvasObject);
          }
        }
        return { canvasObjects: next };
      });
    },

    // --- Select all ---

    selectAllObjects: (): void => {
      const { canvasObjects } = get();
      if (canvasObjects.size === 0) return;
      const allIds = new Set<string>(canvasObjects.keys());
      set({ selectedObjectIds: allIds });
    },

    // --- Multi-object move ---

    moveSelectedObjects: (dx: number, dy: number): void => {
      const { selectedObjectIds, canvasObjects, objectGroups } = get();
      if (selectedObjectIds.size === 0) return;

      // Expand movement to visual groups and semantic-container subtrees.
      const idsToMove = new Set<string>(selectedObjectIds);
      const pendingDescendants = [...selectedObjectIds];
      while (pendingDescendants.length > 0) {
        const parentId = pendingDescendants.pop()!;
        for (const child of canvasObjects.values()) {
          if ('parentContainerId' in child && child.parentContainerId === parentId && !idsToMove.has(child.id)) {
            idsToMove.add(child.id);
            pendingDescendants.push(child.id);
          }
        }
      }
      for (const id of selectedObjectIds) {
        const obj = canvasObjects.get(id);
        if (obj?.groupId) {
          const group = objectGroups.get(obj.groupId);
          if (group) {
            for (const memberId of group.memberIds) {
              idsToMove.add(memberId);
            }
          }
        }
      }

      set((state) => {
        const next = new Map(state.canvasObjects);
        for (const id of idsToMove) {
          const obj = next.get(id);
          if (!obj) continue;
          if (obj.locked) continue;

          if (obj.objectType === 'line') {
            next.set(id, {
              ...obj,
              start: { x: obj.start.x + dx, y: obj.start.y + dy },
              end: { x: obj.end.x + dx, y: obj.end.y + dy },
            });
          } else {
            // architecture-block, geometric, text, uml
            next.set(id, {
              ...obj,
              position: { x: obj.position.x + dx, y: obj.position.y + dy },
            } as CanvasObject);
          }
        }
        return { canvasObjects: next };
      });

      // Identify lines whose BOTH endpoints are moving — their waypoints should
      // be translated (not cleared) since relative geometry is unchanged.
      const bothEndsMovingWaypoints = new Map<string, Point[]>();
      for (const obj of get().canvasObjects.values()) {
        if (obj.objectType !== 'line') continue;
        if (!obj.waypoints || obj.waypoints.length === 0) continue;
        const sourceMoving = obj.sourceAnchor && idsToMove.has(obj.sourceAnchor.objectId);
        const targetMoving = obj.targetAnchor && idsToMove.has(obj.targetAnchor.objectId);
        if (sourceMoving && targetMoving) {
          bothEndsMovingWaypoints.set(obj.id, obj.waypoints.map((wp) => ({ x: wp.x + dx, y: wp.y + dy })));
        }
      }

      // Recompute anchored endpoints for each moved non-line object
      for (const id of idsToMove) {
        const obj = get().canvasObjects.get(id);
        if (obj && obj.objectType !== 'line') {
          get().recomputeAnchoredEndpoints(id);
        }
      }

      // Restore translated waypoints for lines whose both ends moved
      if (bothEndsMovingWaypoints.size > 0) {
        set((state) => {
          const next = new Map(state.canvasObjects);
          for (const [lineId, translatedWaypoints] of bothEndsMovingWaypoints) {
            const line = next.get(lineId);
            if (line && line.objectType === 'line') {
              next.set(lineId, { ...line, waypoints: translatedWaypoints });
            }
          }
          return { canvasObjects: next };
        });
      }
    },

    // --- Text editing ---
    editingTextId: null as string | null,

    setEditingTextId: (id: string | null): void => {
      set({ editingTextId: id });
    },

    updateTextContent: (id: string, content: string): void => {
      const existing = get().canvasObjects.get(id);
      if (!existing || existing.objectType !== 'text') return;

      // If content is empty or whitespace-only, auto-remove the text object
      if (!content || content.trim() === '') {
        get().removeCanvasObject(id);
        return;
      }

      get().pushHistory();
      set((state) => {
        const next = new Map(state.canvasObjects);
        next.set(id, { ...existing, content } as import('@/types/diagram').TextObject);
        return { canvasObjects: next };
      });
    },
});
