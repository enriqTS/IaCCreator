import { describe, it, expect, beforeEach } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';
import type { ArchitectureBlock, LineObject, GeometricObject } from '@/types/diagram';
import { DEFAULT_BLOCK_VISUAL, DEFAULT_LINE_VISUAL, DEFAULT_GEO_VISUAL, MIN_OBJECT_WIDTH, MIN_OBJECT_HEIGHT } from '@/types/diagram';

function resetStore() {
  useDiagramStore.setState({
    canvasObjects: new Map(),
    connectors: new Map(),
    elements: new Map(),
    selectedObjectId: null,
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
}

function addBlock(): string {
  return useDiagramStore.getState().addCanvasObject({
    objectType: 'architecture-block',
    serviceType: 'lambda',
    name: 'lambda-1',
    position: { x: 0, y: 0 },
    config: {},
    visualConfig: { ...DEFAULT_BLOCK_VISUAL },
  } as Omit<ArchitectureBlock, 'id'>);
}

function addLine(): string {
  return useDiagramStore.getState().addCanvasObject({
    objectType: 'line',
    name: 'line-1',
    start: { x: 0, y: 0 },
    end: { x: 100, y: 100 },
    visualConfig: { ...DEFAULT_LINE_VISUAL },
  } as Omit<LineObject, 'id'>);
}

function addGeo(): string {
  return useDiagramStore.getState().addCanvasObject({
    objectType: 'geometric',
    name: 'rect-1',
    position: { x: 50, y: 50 },
    visualConfig: { ...DEFAULT_GEO_VISUAL },
  } as Omit<GeometricObject, 'id'>);
}

describe('DiagramStore - updateVisualConfig', () => {
  beforeEach(resetStore);

  it('merges partial config for architecture block', () => {
    const id = addBlock();
    useDiagramStore.getState().updateVisualConfig(id, { width: 120 });
    const obj = useDiagramStore.getState().canvasObjects.get(id) as ArchitectureBlock;
    expect(obj.visualConfig.width).toBe(120);
    expect(obj.visualConfig.height).toBe(DEFAULT_BLOCK_VISUAL.height);
  });

  it('merges partial config for line', () => {
    const id = addLine();
    useDiagramStore.getState().updateVisualConfig(id, { color: '#ff0000', borderWidth: 5 });
    const obj = useDiagramStore.getState().canvasObjects.get(id) as LineObject;
    expect(obj.visualConfig.color).toBe('#ff0000');
    expect(obj.visualConfig.borderWidth).toBe(5);
    expect(obj.visualConfig.strokeStyle).toBe('solid');
    expect(obj.visualConfig.startArrow).toBe(false);
  });

  it('merges partial config for geometric object', () => {
    const id = addGeo();
    useDiagramStore.getState().updateVisualConfig(id, { fill: true, fillColor: '#00ff00' });
    const obj = useDiagramStore.getState().canvasObjects.get(id) as GeometricObject;
    expect(obj.visualConfig.fill).toBe(true);
    expect(obj.visualConfig.fillColor).toBe('#00ff00');
    expect(obj.visualConfig.borderColor).toBe(DEFAULT_GEO_VISUAL.borderColor);
  });

  it('enforces min dimensions on architecture block', () => {
    const id = addBlock();
    useDiagramStore.getState().updateVisualConfig(id, { width: 10, height: 5 });
    const obj = useDiagramStore.getState().canvasObjects.get(id) as ArchitectureBlock;
    expect(obj.visualConfig.width).toBe(MIN_OBJECT_WIDTH);
    expect(obj.visualConfig.height).toBe(MIN_OBJECT_HEIGHT);
  });

  it('enforces min dimensions on geometric object', () => {
    const id = addGeo();
    useDiagramStore.getState().updateVisualConfig(id, { width: 0, height: -10 });
    const obj = useDiagramStore.getState().canvasObjects.get(id) as GeometricObject;
    expect(obj.visualConfig.width).toBe(MIN_OBJECT_WIDTH);
    expect(obj.visualConfig.height).toBe(MIN_OBJECT_HEIGHT);
  });

  it('is no-op for non-existent id', () => {
    const sizeBefore = useDiagramStore.getState().canvasObjects.size;
    useDiagramStore.getState().updateVisualConfig('nonexistent', { width: 200 });
    expect(useDiagramStore.getState().canvasObjects.size).toBe(sizeBefore);
  });
});

describe('DiagramStore - updateObjectBounds', () => {
  beforeEach(resetStore);

  it('updates width and height for architecture block', () => {
    const id = addBlock();
    useDiagramStore.getState().updateObjectBounds(id, { width: 200, height: 150 });
    const obj = useDiagramStore.getState().canvasObjects.get(id) as ArchitectureBlock;
    expect(obj.visualConfig.width).toBe(200);
    expect(obj.visualConfig.height).toBe(150);
  });

  it('updates only width when height is omitted', () => {
    const id = addGeo();
    useDiagramStore.getState().updateObjectBounds(id, { width: 300 });
    const obj = useDiagramStore.getState().canvasObjects.get(id) as GeometricObject;
    expect(obj.visualConfig.width).toBe(300);
    expect(obj.visualConfig.height).toBe(DEFAULT_GEO_VISUAL.height);
  });

  it('clamps to minimum dimensions', () => {
    const id = addBlock();
    useDiagramStore.getState().updateObjectBounds(id, { width: 10, height: 5 });
    const obj = useDiagramStore.getState().canvasObjects.get(id) as ArchitectureBlock;
    expect(obj.visualConfig.width).toBe(MIN_OBJECT_WIDTH);
    expect(obj.visualConfig.height).toBe(MIN_OBJECT_HEIGHT);
  });

  it('is no-op for line objects', () => {
    const id = addLine();
    const before = useDiagramStore.getState().canvasObjects.get(id) as LineObject;
    useDiagramStore.getState().updateObjectBounds(id, { width: 200, height: 200 });
    const after = useDiagramStore.getState().canvasObjects.get(id) as LineObject;
    expect(after).toEqual(before);
  });

  it('is no-op for non-existent id', () => {
    const sizeBefore = useDiagramStore.getState().canvasObjects.size;
    useDiagramStore.getState().updateObjectBounds('nonexistent', { width: 200 });
    expect(useDiagramStore.getState().canvasObjects.size).toBe(sizeBefore);
  });
});

describe('DiagramStore - updateLineEndpoint', () => {
  beforeEach(resetStore);

  it('updates start endpoint', () => {
    const id = addLine();
    useDiagramStore.getState().updateLineEndpoint(id, 'start', { x: 50, y: 75 });
    const obj = useDiagramStore.getState().canvasObjects.get(id) as LineObject;
    expect(obj.start).toEqual({ x: 50, y: 75 });
    expect(obj.end).toEqual({ x: 100, y: 100 });
  });

  it('updates end endpoint', () => {
    const id = addLine();
    useDiagramStore.getState().updateLineEndpoint(id, 'end', { x: 200, y: 300 });
    const obj = useDiagramStore.getState().canvasObjects.get(id) as LineObject;
    expect(obj.start).toEqual({ x: 0, y: 0 });
    expect(obj.end).toEqual({ x: 200, y: 300 });
  });

  it('is no-op for non-line objects', () => {
    const id = addBlock();
    const before = useDiagramStore.getState().canvasObjects.get(id);
    useDiagramStore.getState().updateLineEndpoint(id, 'start', { x: 999, y: 999 });
    const after = useDiagramStore.getState().canvasObjects.get(id);
    expect(after).toEqual(before);
  });

  it('is no-op for non-existent id', () => {
    const sizeBefore = useDiagramStore.getState().canvasObjects.size;
    useDiagramStore.getState().updateLineEndpoint('nonexistent', 'start', { x: 0, y: 0 });
    expect(useDiagramStore.getState().canvasObjects.size).toBe(sizeBefore);
  });
});

describe('DiagramStore - removeCanvasObject cascade and selection clearing', () => {
  beforeEach(resetStore);

  it('cascade-deletes connectors when removing architecture block', () => {
    // Add two architecture blocks as elements (for connector validation) and as canvas objects
    const elemId1 = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    const elemId2 = useDiagramStore.getState().addElement('s3', { x: 100, y: 0 });

    // Add connectors between the elements
    const cid1 = useDiagramStore.getState().addConnector(elemId1, elemId2);

    // Add corresponding canvas objects with the same IDs
    useDiagramStore.setState((state) => {
      const next = new Map(state.canvasObjects);
      next.set(elemId1, {
        id: elemId1,
        objectType: 'architecture-block',
        serviceType: 'lambda',
        name: 'lambda-1',
        position: { x: 0, y: 0 },
        config: {},
        visualConfig: { ...DEFAULT_BLOCK_VISUAL },
      } as ArchitectureBlock);
      next.set(elemId2, {
        id: elemId2,
        objectType: 'architecture-block',
        serviceType: 's3',
        name: 's3-1',
        position: { x: 100, y: 0 },
        config: {},
        visualConfig: { ...DEFAULT_BLOCK_VISUAL },
      } as ArchitectureBlock);
      return { canvasObjects: next };
    });

    // Remove the first block — should cascade-delete the connector
    useDiagramStore.getState().removeCanvasObject(elemId1);
    expect(useDiagramStore.getState().canvasObjects.has(elemId1)).toBe(false);
    expect(useDiagramStore.getState().connectors.has(cid1)).toBe(false);
    // Second block and element should remain
    expect(useDiagramStore.getState().canvasObjects.has(elemId2)).toBe(true);
  });

  it('does not cascade-delete connectors for non-block objects', () => {
    const elemId1 = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    const elemId2 = useDiagramStore.getState().addElement('s3', { x: 100, y: 0 });
    const cid = useDiagramStore.getState().addConnector(elemId1, elemId2);

    // Add a line object (not a block)
    const lineId = addLine();

    useDiagramStore.getState().removeCanvasObject(lineId);
    // Connector should still exist
    expect(useDiagramStore.getState().connectors.has(cid)).toBe(true);
  });

  it('clears selectedObjectId when deleting the selected object', () => {
    const id = addBlock();
    useDiagramStore.getState().selectObject(id);
    expect(useDiagramStore.getState().selectedObjectId).toBe(id);

    useDiagramStore.getState().removeCanvasObject(id);
    expect(useDiagramStore.getState().selectedObjectId).toBeNull();
  });

  it('does not clear selectedObjectId when deleting a different object', () => {
    const id1 = addBlock();
    const id2 = addLine();
    useDiagramStore.getState().selectObject(id1);

    useDiagramStore.getState().removeCanvasObject(id2);
    expect(useDiagramStore.getState().selectedObjectId).toBe(id1);
  });
});
