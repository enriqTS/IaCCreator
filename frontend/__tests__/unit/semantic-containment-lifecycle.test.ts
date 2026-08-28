import { beforeEach, describe, expect, it } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';
import type { ArchitectureBlock, CanvasObject, Connector, SemanticContainerObject } from '@/types/diagram';
import { collectObstacles } from '@/utils/routing/routing-obstacles';

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
    serviceType: 'lambda',
    name: id,
    position: { x: 10, y: 20 },
    config: {},
    terraformVariables: {},
    visualConfig: visual,
    zIndex: 1,
    parentContainerId,
  };
}

function reset(objects: CanvasObject[] = [], connectors: Connector[] = []) {
  useDiagramStore.setState({
    canvasObjects: new Map(objects.map((object) => [object.id, object])),
    connectors: new Map(connectors.map((connector) => [connector.id, connector])),
    selectedObjectIds: new Set(),
    objectGroups: new Map(),
    clipboard: [],
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
}

describe('semantic containment lifecycle', () => {
  beforeEach(() => reset());

  it('reparents descendants and removes managed connectors when a container is deleted', () => {
    const region = container('region');
    const subnet = container('subnet', 'region');
    const workload = resource('workload', 'subnet');
    reset([region, subnet, workload], [{ id: 'managed', sourceId: 'subnet', targetId: 'workload', connectionType: 'places', origin: 'containment' }]);

    useDiagramStore.getState().removeCanvasObject('subnet');

    expect(useDiagramStore.getState().canvasObjects.get('workload')?.parentContainerId).toBe('region');
    expect(useDiagramStore.getState().connectors.has('managed')).toBe(false);
  });

  it('supports cascade deletion when a complete subtree is selected', () => {
    const root = container('root');
    const nested = container('nested', 'root');
    const child = resource('child', 'nested');
    reset([root, nested, child]);

    useDiagramStore.getState().removeMultipleCanvasObjects(new Set(['root', 'nested', 'child']));

    expect(useDiagramStore.getState().canvasObjects.size).toBe(0);
  });

  it('preserves internal parents for a complete subtree and clears them for partial copies', () => {
    const root = container('root');
    const child = resource('child', 'root');
    reset([root, child]);
    useDiagramStore.setState({ selectedObjectIds: new Set(['root', 'child']) });
    useDiagramStore.getState().copySelectedObjects();
    useDiagramStore.getState().pasteObjects({ x: 300, y: 300 });

    const pasted = [...useDiagramStore.getState().selectedObjectIds].map((id) => useDiagramStore.getState().canvasObjects.get(id)!);
    const pastedRoot = pasted.find((object) => object.objectType === 'semantic-container')!;
    const pastedChild = pasted.find((object) => object.objectType === 'architecture-block')!;
    expect(pastedChild.parentContainerId).toBe(pastedRoot.id);

    reset([root, child]);
    useDiagramStore.setState({ selectedObjectIds: new Set(['child']) });
    useDiagramStore.getState().copySelectedObjects();
    useDiagramStore.getState().pasteObjects({ x: 300, y: 300 });
    const partialId = [...useDiagramStore.getState().selectedObjectIds][0];
    expect(useDiagramStore.getState().canvasObjects.get(partialId)?.parentContainerId).toBeUndefined();
  });

  it('restores hierarchy, collapse state, and connectors through undo and redo', () => {
    const root = { ...container('root'), collapsed: true };
    const child = resource('child', 'root');
    reset([root, child], [{ id: 'managed', sourceId: 'root', targetId: 'child', connectionType: 'contains', origin: 'containment' }]);

    useDiagramStore.getState().removeCanvasObject('root');
    useDiagramStore.getState().undo();
    expect(useDiagramStore.getState().canvasObjects.get('root')?.collapsed).toBe(true);
    expect(useDiagramStore.getState().canvasObjects.get('child')?.parentContainerId).toBe('root');
    expect(useDiagramStore.getState().connectors.has('managed')).toBe(true);
    useDiagramStore.getState().redo();
    expect(useDiagramStore.getState().canvasObjects.has('root')).toBe(false);
  });

  it('resizes a boundary without changing descendant geometry', () => {
    const root = container('root');
    const child = resource('child', 'root');
    reset([root, child]);
    const originalPosition = child.position;
    const originalSize = child.visualConfig;

    useDiagramStore.getState().updateObjectBounds('root', { width: 400, height: 300 });

    expect(useDiagramStore.getState().canvasObjects.get('child')?.position).toEqual(originalPosition);
    expect(useDiagramStore.getState().canvasObjects.get('child')?.visualConfig).toEqual(originalSize);
  });

  it('keeps semantic boundaries out of routing obstacles', () => {
    const scope = container('scope');
    const vpc = { ...resource('vpc'), serviceType: 'vpc' as const, presentation: 'container' as const };
    const child = resource('child', 'scope');
    const obstacles = collectObstacles(new Map([[scope.id, scope], [vpc.id, vpc], [child.id, child]]), new Set());

    expect(obstacles).toHaveLength(1);
  });
});
