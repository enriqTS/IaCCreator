import type { CanvasObject } from '@/types/diagram';

function isContainer(object: CanvasObject): boolean {
  return object.objectType === 'semantic-container'
    || (object.objectType === 'architecture-block' && object.presentation === 'container');
}

export function normalizeSemanticZOrder(objects: Map<string, CanvasObject>): Map<string, CanvasObject> {
  const ordered = Array.from(objects.values()).sort((a, b) => a.zIndex - b.zIndex);
  const children = new Map<string, CanvasObject[]>();
  for (const object of ordered) {
    if (!('parentContainerId' in object) || !object.parentContainerId) continue;
    const siblings = children.get(object.parentContainerId) ?? [];
    siblings.push(object);
    children.set(object.parentContainerId, siblings);
  }

  const result: CanvasObject[] = [];
  const visited = new Set<string>();
  const visit = (object: CanvasObject) => {
    if (visited.has(object.id)) return;
    visited.add(object.id);
    result.push(object);
    for (const child of children.get(object.id) ?? []) visit(child);
  };
  for (const object of ordered.filter(isContainer)) {
    const parentId = 'parentContainerId' in object ? object.parentContainerId : undefined;
    if (!parentId || !objects.has(parentId)) visit(object);
  }
  for (const object of ordered) visit(object);

  return new Map(result.map((object, zIndex) => [object.id, { ...object, zIndex } as CanvasObject]));
}
