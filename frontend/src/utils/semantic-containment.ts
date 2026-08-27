import type { CanvasObject } from '@/types/diagram';

export function normalizeSemanticZOrder(objects: Map<string, CanvasObject>): Map<string, CanvasObject> {
  const result = new Map(objects);
  const resolving = new Set<string>();

  const ensureParentBelow = (object: CanvasObject): number => {
    const parentId = 'parentContainerId' in object ? object.parentContainerId : undefined;
    if (!parentId) return object.zIndex;
    const parent = result.get(parentId);
    if (!parent || resolving.has(object.id)) return object.zIndex;

    resolving.add(object.id);
    const parentZ = ensureParentBelow(parent);
    resolving.delete(object.id);
    if (parentZ < object.zIndex) return object.zIndex;

    const adjusted = { ...parent, zIndex: object.zIndex - 1 } as CanvasObject;
    result.set(parent.id, adjusted);
    ensureParentBelow(adjusted);
    return object.zIndex;
  };

  for (const object of result.values()) ensureParentBelow(object);
  return result;
}
