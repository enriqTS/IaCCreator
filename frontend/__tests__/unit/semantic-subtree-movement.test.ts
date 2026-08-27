import { beforeEach, describe, expect, it } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';
import type { ArchitectureBlock, CanvasObject, SemanticContainerObject } from '@/types/diagram';

const visual = { width: 100, height: 100 };

function container(id: string, parentContainerId?: string): SemanticContainerObject {
  return {
    id,
    objectType: 'semantic-container',
    containerType: 'generic',
    name: id,
    position: { x: 0, y: 0 },
    config: {},
    visualConfig: { ...visual, fillColor: '#000', borderColor: '#fff', borderWidth: 1 },
    zIndex: 0,
    parentContainerId,
  };
}

function resource(id: string, parentContainerId?: string): ArchitectureBlock {
  return {
    id,
    objectType: 'architecture-block',
    serviceType: 'ec2',
    name: id,
    position: { x: 10, y: 20 },
    config: {},
    terraformVariables: {},
    visualConfig: visual,
    zIndex: 1,
    parentContainerId,
  };
}

describe('semantic subtree movement', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
      objectGroups: new Map(),
    });
  });

  it('moves every descendant once without changing selection', () => {
    const parent = container('parent');
    const nested = container('nested', 'parent');
    const child = resource('child', 'nested');
    useDiagramStore.setState({
      canvasObjects: new Map<string, CanvasObject>([[parent.id, parent], [nested.id, nested], [child.id, child]]),
      selectedObjectIds: new Set(['parent']),
    });

    useDiagramStore.getState().moveSelectedObjects(15, -5);

    const objects = useDiagramStore.getState().canvasObjects;
    expect((objects.get('parent') as SemanticContainerObject).position).toEqual({ x: 15, y: -5 });
    expect((objects.get('nested') as SemanticContainerObject).position).toEqual({ x: 15, y: -5 });
    expect((objects.get('child') as ArchitectureBlock).position).toEqual({ x: 25, y: 15 });
    expect(useDiagramStore.getState().selectedObjectIds).toEqual(new Set(['parent']));
  });
});
