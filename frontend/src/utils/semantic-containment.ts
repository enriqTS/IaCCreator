import type { CanvasObject, Rect } from '@/types/diagram';
import { getObjectBounds } from '@/types/diagram';

export interface ContainmentPlacementRule {
  child_type: string;
  parent_type: string;
}

export interface ContainmentDropCandidate {
  id: string;
  valid: boolean;
  depth: number;
}

export function semanticType(object: CanvasObject): string {
  if (object.objectType === 'semantic-container') return object.containerType;
  if (object.objectType === 'architecture-block') return object.serviceType;
  return 'visual';
}

export function isSemanticContainer(object: CanvasObject): boolean {
  return object.objectType === 'semantic-container'
    || (object.objectType === 'architecture-block'
      && object.presentation === 'container'
      && (object.serviceType === 'vpc' || object.serviceType === 'subnet'));
}

export function containmentDepth(object: CanvasObject, objects: Map<string, CanvasObject>): number {
  let depth = 0;
  let current: CanvasObject | undefined = object;
  const visited = new Set<string>();
  while (current && 'parentContainerId' in current && current.parentContainerId && !visited.has(current.id)) {
    visited.add(current.id);
    depth += 1;
    current = objects.get(current.parentContainerId);
  }
  return depth;
}

export function overlapRatio(inner: Rect, outer: Rect): number {
  const width = Math.max(0, Math.min(inner.x + inner.width, outer.x + outer.width) - Math.max(inner.x, outer.x));
  const height = Math.max(0, Math.min(inner.y + inner.height, outer.y + outer.height) - Math.max(inner.y, outer.y));
  const area = inner.width * inner.height;
  return area > 0 ? (width * height) / area : 0;
}

export function findContainmentDropCandidate(
  objectId: string,
  objects: Map<string, CanvasObject>,
  rules: ContainmentPlacementRule[],
  threshold = 0.5,
): ContainmentDropCandidate | null {
  const object = objects.get(objectId);
  if (!object || object.objectType === 'line') return null;
  const bounds = getObjectBounds(object);
  const descendants = new Set<string>();
  const queue = [objectId];
  while (queue.length > 0) {
    const parentId = queue.pop()!;
    for (const child of objects.values()) {
      if ('parentContainerId' in child && child.parentContainerId === parentId && !descendants.has(child.id)) {
        descendants.add(child.id);
        queue.push(child.id);
      }
    }
  }
  const childType = semanticType(object);
  const candidates = [...objects.values()]
    .filter((candidate) => candidate.id !== objectId && !descendants.has(candidate.id) && isSemanticContainer(candidate))
    .filter((candidate) => overlapRatio(bounds, getObjectBounds(candidate)) >= threshold)
    .map((candidate) => ({
      id: candidate.id,
      valid: rules.some((rule) => rule.child_type === childType && rule.parent_type === semanticType(candidate)),
      depth: containmentDepth(candidate, objects),
    }))
    .sort((a, b) => b.depth - a.depth || Number(b.valid) - Number(a.valid) || a.id.localeCompare(b.id));
  return candidates[0] ?? null;
}

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
