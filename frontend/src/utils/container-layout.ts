import { getObjectBounds } from '@/types/diagram';
import type { CanvasObject, Point } from '@/types/diagram';
import { isSemanticContainer, semanticType } from '@/utils/semantic-containment';

const PADDING = 32;
const HEADER_HEIGHT = 48;
const GAP = 24;

function positionOf(object: CanvasObject): Point | null {
  return 'position' in object ? object.position : null;
}

function descendantsOf(parentId: string, objects: Map<string, CanvasObject>): CanvasObject[] {
  const descendants: CanvasObject[] = [];
  const queue = [parentId];
  while (queue.length > 0) {
    const current = queue.shift()!;
    for (const object of objects.values()) {
      if ('parentContainerId' in object && object.parentContainerId === current) {
        descendants.push(object);
        queue.push(object.id);
      }
    }
  }
  return descendants;
}

export function layoutContainerChildren(
  containerId: string,
  objects: Map<string, CanvasObject>,
): Map<string, CanvasObject> {
  const container = objects.get(containerId);
  if (!container || !isSemanticContainer(container)) return objects;
  const children = [...objects.values()]
    .filter((object) => 'parentContainerId' in object && object.parentContainerId === containerId)
    .filter((object) => positionOf(object) !== null)
    .sort((a, b) => semanticType(a).localeCompare(semanticType(b))
      || a.name.localeCompare(b.name)
      || a.id.localeCompare(b.id));
  if (children.length === 0) return objects;

  const columns = Math.ceil(Math.sqrt(children.length));
  const rows = Math.ceil(children.length / columns);
  const cellWidth = Math.max(...children.map((child) => getObjectBounds(child).width));
  const cellHeight = Math.max(...children.map((child) => getObjectBounds(child).height));
  const width = Math.max(container.visualConfig.width, PADDING * 2 + columns * cellWidth + (columns - 1) * GAP);
  const height = Math.max(container.visualConfig.height, HEADER_HEIGHT + PADDING + rows * cellHeight + (rows - 1) * GAP);
  const left = container.position.x - width / 2 + PADDING;
  const top = container.position.y - height / 2 + HEADER_HEIGHT;
  const result = new Map(objects);
  result.set(containerId, {
    ...container,
    visualConfig: { ...container.visualConfig, width, height },
  } as CanvasObject);

  children.forEach((child, index) => {
    const oldPosition = positionOf(child)!;
    const column = index % columns;
    const row = Math.floor(index / columns);
    const newPosition = {
      x: left + column * (cellWidth + GAP) + cellWidth / 2,
      y: top + row * (cellHeight + GAP) + cellHeight / 2,
    };
    const delta = { x: newPosition.x - oldPosition.x, y: newPosition.y - oldPosition.y };
    result.set(child.id, { ...child, position: newPosition } as CanvasObject);
    if (isSemanticContainer(child)) {
      for (const descendant of descendantsOf(child.id, objects)) {
        const position = positionOf(descendant);
        if (position) {
          result.set(descendant.id, {
            ...descendant,
            position: { x: position.x + delta.x, y: position.y + delta.y },
          } as CanvasObject);
        }
      }
    }
  });
  return result;
}
