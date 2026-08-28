import { describe, expect, it } from 'vitest';
import type { ArchitectureBlock, CanvasObject, SemanticContainerObject } from '@/types/diagram';
import { layoutContainerChildren } from '@/utils/container-layout';

function container(id: string, parentContainerId?: string): SemanticContainerObject {
  return {
    id,
    objectType: 'semantic-container',
    containerType: 'generic',
    name: id,
    position: { x: 300, y: 250 },
    config: {},
    visualConfig: { width: 200, height: 150, fillColor: '#000', borderColor: '#fff', borderWidth: 1 },
    zIndex: 0,
    parentContainerId,
  };
}

function resource(id: string, name: string, parentContainerId: string): ArchitectureBlock {
  return {
    id,
    objectType: 'architecture-block',
    serviceType: 'ec2',
    name,
    position: { x: 0, y: 0 },
    config: {},
    terraformVariables: {},
    visualConfig: { width: 80, height: 80 },
    zIndex: 1,
    parentContainerId,
  };
}

describe('layoutContainerChildren', () => {
  it('lays out direct children deterministically and expands the boundary', () => {
    const parent = container('parent');
    const first = resource('first', 'zeta', parent.id);
    const second = resource('second', 'alpha', parent.id);
    const objects = new Map<string, CanvasObject>([
      [parent.id, parent],
      [first.id, first],
      [second.id, second],
    ]);

    const result = layoutContainerChildren(parent.id, objects);

    expect(result.get('second')!.position.x).toBeLessThan(result.get('first')!.position.x);
    expect(result.get('parent')!.visualConfig.width).toBeGreaterThanOrEqual(248);
    expect(result.get('parent')!.visualConfig.height).toBeGreaterThanOrEqual(160);
  });

  it('moves a nested container subtree without changing its internal geometry', () => {
    const parent = container('parent');
    const nested = { ...container('nested', parent.id), position: { x: 20, y: 20 } };
    const child = { ...resource('child', 'child', nested.id), position: { x: 40, y: 50 } };
    const objects = new Map<string, CanvasObject>([
      [parent.id, parent],
      [nested.id, nested],
      [child.id, child],
    ]);

    const result = layoutContainerChildren(parent.id, objects);
    const movedNested = result.get(nested.id)!;
    const movedChild = result.get(child.id)!;

    expect(movedChild.position.x - movedNested.position.x).toBe(20);
    expect(movedChild.position.y - movedNested.position.y).toBe(30);
  });
});
