import { describe, it, expect, beforeEach } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';

describe('DiagramStore - Element Operations', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      elements: new Map(),
      connectors: new Map(),
    });
  });

  it('addElement creates element with correct serviceType and position', () => {
    const id = useDiagramStore.getState().addElement('lambda', { x: 100, y: 200 });
    const el = useDiagramStore.getState().elements.get(id);

    expect(el).toBeDefined();
    expect(el!.serviceType).toBe('lambda');
    expect(el!.position).toEqual({ x: 100, y: 200 });
    expect(el!.config).toEqual({});
  });

  it('addElement generates default name {serviceType}-{n}', () => {
    const id1 = useDiagramStore.getState().addElement('s3', { x: 0, y: 0 });
    const id2 = useDiagramStore.getState().addElement('s3', { x: 10, y: 10 });
    const id3 = useDiagramStore.getState().addElement('lambda', { x: 20, y: 20 });

    expect(useDiagramStore.getState().elements.get(id1)!.name).toBe('s3-1');
    expect(useDiagramStore.getState().elements.get(id2)!.name).toBe('s3-2');
    expect(useDiagramStore.getState().elements.get(id3)!.name).toBe('lambda-1');
  });

  it('addElement generates unique IDs', () => {
    const id1 = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    const id2 = useDiagramStore.getState().addElement('lambda', { x: 10, y: 10 });
    expect(id1).not.toBe(id2);
  });

  it('updateElementPosition updates only position', () => {
    const id = useDiagramStore.getState().addElement('dynamodb', { x: 0, y: 0 });
    useDiagramStore.getState().updateElementPosition(id, { x: 500, y: 300 });

    const el = useDiagramStore.getState().elements.get(id)!;
    expect(el.position).toEqual({ x: 500, y: 300 });
    expect(el.serviceType).toBe('dynamodb');
    expect(el.name).toBe('dynamodb-1');
  });

  it('updateElementPosition is no-op for non-existent element', () => {
    useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    const before = new Map(useDiagramStore.getState().elements);
    useDiagramStore.getState().updateElementPosition('nonexistent', { x: 1, y: 1 });
    expect(useDiagramStore.getState().elements).toEqual(before);
  });

  it('updateElementConfig merges config fields', () => {
    const id = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    useDiagramStore.getState().updateElementConfig(id, { handler: 'index.handler' });
    useDiagramStore.getState().updateElementConfig(id, { runtime: 'nodejs20.x' });

    const el = useDiagramStore.getState().elements.get(id)!;
    expect(el.config.handler).toBe('index.handler');
    expect(el.config.runtime).toBe('nodejs20.x');
  });

  it('updateElementName changes the name', () => {
    const id = useDiagramStore.getState().addElement('s3', { x: 0, y: 0 });
    useDiagramStore.getState().updateElementName(id, 'my-bucket');
    expect(useDiagramStore.getState().elements.get(id)!.name).toBe('my-bucket');
  });

  it('removeElement deletes the element', () => {
    const id = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    useDiagramStore.getState().removeElement(id);
    expect(useDiagramStore.getState().elements.has(id)).toBe(false);
    expect(useDiagramStore.getState().elements.size).toBe(0);
  });

  it('removeElement cascades to connectors', () => {
    const id1 = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    const id2 = useDiagramStore.getState().addElement('s3', { x: 100, y: 0 });
    const id3 = useDiagramStore.getState().addElement('dynamodb', { x: 200, y: 0 });

    const c1 = useDiagramStore.getState().addConnector(id1, id2);
    const c2 = useDiagramStore.getState().addConnector(id2, id3);
    const c3 = useDiagramStore.getState().addConnector(id1, id3);

    // Remove id1 — should cascade c1 (source) and c3 (source)
    useDiagramStore.getState().removeElement(id1);

    expect(useDiagramStore.getState().connectors.has(c1)).toBe(false);
    expect(useDiagramStore.getState().connectors.has(c3)).toBe(false);
    // c2 should remain (id2 → id3)
    expect(useDiagramStore.getState().connectors.has(c2)).toBe(true);
  });

  it('removeElement is no-op for non-existent element', () => {
    useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    const sizeBefore = useDiagramStore.getState().elements.size;
    useDiagramStore.getState().removeElement('nonexistent');
    expect(useDiagramStore.getState().elements.size).toBe(sizeBefore);
  });
});

describe('DiagramStore - Connector Operations', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      elements: new Map(),
      connectors: new Map(),
    });
  });

  it('addConnector creates connector with default connectionType "triggers"', () => {
    const id1 = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    const id2 = useDiagramStore.getState().addElement('s3', { x: 100, y: 0 });

    const cid = useDiagramStore.getState().addConnector(id1, id2);
    const conn = useDiagramStore.getState().connectors.get(cid)!;

    expect(conn.sourceId).toBe(id1);
    expect(conn.targetId).toBe(id2);
    expect(conn.connectionType).toBe('triggers');
  });

  it('addConnector uses provided connectionType', () => {
    const id1 = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    const id2 = useDiagramStore.getState().addElement('dynamodb', { x: 100, y: 0 });

    const cid = useDiagramStore.getState().addConnector(id1, id2, 'reads_from');
    expect(useDiagramStore.getState().connectors.get(cid)!.connectionType).toBe('reads_from');
  });

  it('addConnector rejects self-connections', () => {
    const id = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    expect(() => useDiagramStore.getState().addConnector(id, id)).toThrow();
  });

  it('addConnector rejects non-existent source', () => {
    const id = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    expect(() => useDiagramStore.getState().addConnector('nonexistent', id)).toThrow();
  });

  it('addConnector rejects non-existent target', () => {
    const id = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    expect(() => useDiagramStore.getState().addConnector(id, 'nonexistent')).toThrow();
  });

  it('updateConnectorType changes the connectionType', () => {
    const id1 = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    const id2 = useDiagramStore.getState().addElement('s3', { x: 100, y: 0 });
    const cid = useDiagramStore.getState().addConnector(id1, id2);

    useDiagramStore.getState().updateConnectorType(cid, 'writes_to');
    expect(useDiagramStore.getState().connectors.get(cid)!.connectionType).toBe('writes_to');
  });

  it('removeConnector deletes only the connector', () => {
    const id1 = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    const id2 = useDiagramStore.getState().addElement('s3', { x: 100, y: 0 });
    const cid = useDiagramStore.getState().addConnector(id1, id2);

    useDiagramStore.getState().removeConnector(cid);

    expect(useDiagramStore.getState().connectors.has(cid)).toBe(false);
    // Elements should remain
    expect(useDiagramStore.getState().elements.has(id1)).toBe(true);
    expect(useDiagramStore.getState().elements.has(id2)).toBe(true);
  });
});

describe('DiagramStore - Viewport State', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      elements: new Map(),
      connectors: new Map(),
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
      canUndo: false,
      canRedo: false,
    });
  });

  it('has default viewport { offsetX: 0, offsetY: 0, scale: 1.0 }', () => {
    const { viewport } = useDiagramStore.getState();
    expect(viewport).toEqual({ offsetX: 0, offsetY: 0, scale: 1.0 });
  });

  it('pan adds dx and dy to offset', () => {
    useDiagramStore.getState().pan(50, -30);
    const { viewport } = useDiagramStore.getState();
    expect(viewport.offsetX).toBe(50);
    expect(viewport.offsetY).toBe(-30);
    expect(viewport.scale).toBe(1.0);
  });

  it('pan accumulates across calls', () => {
    useDiagramStore.getState().pan(10, 20);
    useDiagramStore.getState().pan(5, -10);
    const { viewport } = useDiagramStore.getState();
    expect(viewport.offsetX).toBe(15);
    expect(viewport.offsetY).toBe(10);
  });

  it('zoom changes scale using zoomAtPoint', () => {
    useDiagramStore.getState().zoom(2.0, { x: 0, y: 0 });
    const { viewport } = useDiagramStore.getState();
    expect(viewport.scale).toBe(2.0);
  });

  it('zoom clamps scale to [0.1, 5.0]', () => {
    useDiagramStore.getState().zoom(10, { x: 0, y: 0 });
    expect(useDiagramStore.getState().viewport.scale).toBe(5.0);

    useDiagramStore.setState({ viewport: { offsetX: 0, offsetY: 0, scale: 1.0 } });
    useDiagramStore.getState().zoom(0.01, { x: 0, y: 0 });
    expect(useDiagramStore.getState().viewport.scale).toBe(0.1);
  });
});

describe('DiagramStore - UI State', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      elements: new Map(),
      connectors: new Map(),
      activeTool: 'pointer',
      selectedElementId: null,
      selectedConnectorId: null,
      pendingConnectorSourceId: null,
      canUndo: false,
      canRedo: false,
    });
  });

  it('default activeTool is pointer', () => {
    expect(useDiagramStore.getState().activeTool).toBe('pointer');
  });

  it('setActiveTool changes the active tool', () => {
    useDiagramStore.getState().setActiveTool('connector');
    expect(useDiagramStore.getState().activeTool).toBe('connector');
  });

  it('setActiveTool supports place-service tool', () => {
    useDiagramStore.getState().setActiveTool({ type: 'place-service', serviceType: 'lambda' });
    expect(useDiagramStore.getState().activeTool).toEqual({ type: 'place-service', serviceType: 'lambda' });
  });

  it('selectElement sets selectedElementId and clears selectedConnectorId', () => {
    useDiagramStore.setState({ selectedConnectorId: 'some-connector' });
    useDiagramStore.getState().selectElement('elem-1');
    expect(useDiagramStore.getState().selectedElementId).toBe('elem-1');
    expect(useDiagramStore.getState().selectedConnectorId).toBeNull();
  });

  it('selectConnector sets selectedConnectorId and clears selectedElementId', () => {
    useDiagramStore.setState({ selectedElementId: 'some-element' });
    useDiagramStore.getState().selectConnector('conn-1');
    expect(useDiagramStore.getState().selectedConnectorId).toBe('conn-1');
    expect(useDiagramStore.getState().selectedElementId).toBeNull();
  });

  it('selectElement with null deselects', () => {
    useDiagramStore.setState({ selectedElementId: 'elem-1' });
    useDiagramStore.getState().selectElement(null);
    expect(useDiagramStore.getState().selectedElementId).toBeNull();
  });

  it('selectConnector with null deselects', () => {
    useDiagramStore.setState({ selectedConnectorId: 'conn-1' });
    useDiagramStore.getState().selectConnector(null);
    expect(useDiagramStore.getState().selectedConnectorId).toBeNull();
  });
});

describe('DiagramStore - Undo/Redo', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      elements: new Map(),
      connectors: new Map(),
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
      activeTool: 'pointer',
      selectedElementId: null,
      selectedConnectorId: null,
      pendingConnectorSourceId: null,
      canUndo: false,
      canRedo: false,
      _undoStack: [],
      _redoStack: [],
    });
  });

  it('canUndo is false initially', () => {
    expect(useDiagramStore.getState().canUndo).toBe(false);
  });

  it('canRedo is false initially', () => {
    expect(useDiagramStore.getState().canRedo).toBe(false);
  });

  it('addElement makes canUndo true', () => {
    useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    expect(useDiagramStore.getState().canUndo).toBe(true);
  });

  it('undo after addElement restores empty state', () => {
    useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    expect(useDiagramStore.getState().elements.size).toBe(1);

    useDiagramStore.getState().undo();
    expect(useDiagramStore.getState().elements.size).toBe(0);
    expect(useDiagramStore.getState().canUndo).toBe(false);
    expect(useDiagramStore.getState().canRedo).toBe(true);
  });

  it('redo after undo restores the element', () => {
    const id = useDiagramStore.getState().addElement('lambda', { x: 10, y: 20 });
    useDiagramStore.getState().undo();
    expect(useDiagramStore.getState().elements.size).toBe(0);

    useDiagramStore.getState().redo();
    expect(useDiagramStore.getState().elements.size).toBe(1);
    // The element should have the same data (though ID may differ since it's a snapshot)
    const el = Array.from(useDiagramStore.getState().elements.values())[0];
    expect(el.serviceType).toBe('lambda');
    expect(el.position).toEqual({ x: 10, y: 20 });
  });

  it('new mutation clears redo stack', () => {
    useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    useDiagramStore.getState().undo();
    expect(useDiagramStore.getState().canRedo).toBe(true);

    // New mutation should clear redo
    useDiagramStore.getState().addElement('s3', { x: 50, y: 50 });
    expect(useDiagramStore.getState().canRedo).toBe(false);
  });

  it('undo restores element position after move', () => {
    const id = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    useDiagramStore.getState().updateElementPosition(id, { x: 100, y: 200 });

    useDiagramStore.getState().undo();
    const el = useDiagramStore.getState().elements.get(id)!;
    expect(el.position).toEqual({ x: 0, y: 0 });
  });

  it('undo restores connectors after removeElement cascade', () => {
    const id1 = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    const id2 = useDiagramStore.getState().addElement('s3', { x: 100, y: 0 });
    const cid = useDiagramStore.getState().addConnector(id1, id2);

    useDiagramStore.getState().removeElement(id1);
    expect(useDiagramStore.getState().elements.size).toBe(1);
    expect(useDiagramStore.getState().connectors.size).toBe(0);

    useDiagramStore.getState().undo();
    expect(useDiagramStore.getState().elements.size).toBe(2);
    expect(useDiagramStore.getState().connectors.size).toBe(1);
  });

  it('undo is no-op when stack is empty', () => {
    const sizeBefore = useDiagramStore.getState().elements.size;
    useDiagramStore.getState().undo();
    expect(useDiagramStore.getState().elements.size).toBe(sizeBefore);
  });

  it('redo is no-op when stack is empty', () => {
    const sizeBefore = useDiagramStore.getState().elements.size;
    useDiagramStore.getState().redo();
    expect(useDiagramStore.getState().elements.size).toBe(sizeBefore);
  });
});

describe('DiagramStore - Project State', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      elements: new Map(),
      connectors: new Map(),
      projectName: '',
      environments: [],
      _undoStack: [],
      _redoStack: [],
      canUndo: false,
      canRedo: false,
    });
  });

  it('default projectName is empty string', () => {
    expect(useDiagramStore.getState().projectName).toBe('');
  });

  it('default environments is empty array', () => {
    expect(useDiagramStore.getState().environments).toEqual([]);
  });

  it('setProjectName updates projectName', () => {
    useDiagramStore.getState().setProjectName('my-project');
    expect(useDiagramStore.getState().projectName).toBe('my-project');
  });

  it('setEnvironments updates environments', () => {
    const envs = [
      { name: 'dev', variables: { region: 'us-east-1' } },
      { name: 'prod', variables: { region: 'us-west-2' } },
    ];
    useDiagramStore.getState().setEnvironments(envs);
    expect(useDiagramStore.getState().environments).toEqual(envs);
  });
});

describe('DiagramStore - serializeDiagramState', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      elements: new Map(),
      connectors: new Map(),
      canvasObjects: new Map(),
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
      projectName: '',
      environments: [],
      _undoStack: [],
      _redoStack: [],
      canUndo: false,
      canRedo: false,
    });
  });

  it('returns DiagramState with version 2', () => {
    const state = useDiagramStore.getState().serializeDiagramState();
    expect(state.version).toBe(2);
  });

  it('serializes empty diagram correctly', () => {
    const state = useDiagramStore.getState().serializeDiagramState();
    expect(state.elements).toEqual([]);
    expect(state.connectors).toEqual([]);
    expect(state.canvasObjects).toEqual([]);
    expect(state.viewport).toEqual({ offsetX: 0, offsetY: 0, scale: 1.0 });
    expect(state.projectName).toBe('');
    expect(state.environments).toEqual([]);
  });

  it('serializes elements as array', () => {
    const id = useDiagramStore.getState().addElement('lambda', { x: 10, y: 20 });
    const state = useDiagramStore.getState().serializeDiagramState();

    expect(state.elements).toHaveLength(1);
    expect(state.elements[0].id).toBe(id);
    expect(state.elements[0].serviceType).toBe('lambda');
    expect(state.elements[0].position).toEqual({ x: 10, y: 20 });
  });

  it('serializes connectors as array', () => {
    const id1 = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    const id2 = useDiagramStore.getState().addElement('s3', { x: 100, y: 0 });
    const cid = useDiagramStore.getState().addConnector(id1, id2, 'writes_to');

    const state = useDiagramStore.getState().serializeDiagramState();
    expect(state.connectors).toHaveLength(1);
    expect(state.connectors[0].id).toBe(cid);
    expect(state.connectors[0].sourceId).toBe(id1);
    expect(state.connectors[0].targetId).toBe(id2);
    expect(state.connectors[0].connectionType).toBe('writes_to');
  });

  it('includes viewport, projectName, and environments', () => {
    useDiagramStore.getState().pan(50, -30);
    useDiagramStore.getState().setProjectName('test-project');
    useDiagramStore.getState().setEnvironments([{ name: 'dev', variables: { key: 'val' } }]);

    const state = useDiagramStore.getState().serializeDiagramState();
    expect(state.viewport.offsetX).toBe(50);
    expect(state.viewport.offsetY).toBe(-30);
    expect(state.projectName).toBe('test-project');
    expect(state.environments).toEqual([{ name: 'dev', variables: { key: 'val' } }]);
  });

  it('serializes canvasObjects as array', () => {
    const id = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'lambda',
      name: 'lambda-1',
      position: { x: 10, y: 20 },
      config: { handler: 'index.handler' },
      visualConfig: { width: 80, height: 80 },
    });
    const state = useDiagramStore.getState().serializeDiagramState();

    expect(state.canvasObjects).toBeDefined();
    expect(state.canvasObjects!).toHaveLength(1);
    expect(state.canvasObjects![0].id).toBe(id);
    expect(state.canvasObjects![0].objectType).toBe('architecture-block');
    expect(state.canvasObjects![0].x).toBe(10);
    expect(state.canvasObjects![0].y).toBe(20);
    expect(state.canvasObjects![0].serviceType).toBe('lambda');
    expect(state.canvasObjects![0].visualConfig).toEqual({ width: 80, height: 80 });
  });
});

describe('DiagramStore - loadDiagramState', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      elements: new Map(),
      connectors: new Map(),
      canvasObjects: new Map(),
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
      projectName: '',
      environments: [],
      _undoStack: [],
      _redoStack: [],
      canUndo: false,
      canRedo: false,
    });
  });

  it('restores elements from serialized state', () => {
    const state = {
      version: 1,
      projectName: 'loaded',
      environments: [],
      elements: [
        { id: 'e1', serviceType: 'lambda' as const, name: 'lambda-1', position: { x: 10, y: 20 }, config: { handler: 'index.handler' } },
      ],
      connectors: [],
      viewport: { offsetX: 5, offsetY: 10, scale: 2.0 },
    };

    useDiagramStore.getState().loadDiagramState(state);

    const el = useDiagramStore.getState().elements.get('e1');
    expect(el).toBeDefined();
    expect(el!.serviceType).toBe('lambda');
    expect(el!.name).toBe('lambda-1');
    expect(el!.position).toEqual({ x: 10, y: 20 });
    expect(el!.config.handler).toBe('index.handler');
  });

  it('restores connectors from serialized state', () => {
    const state = {
      version: 1,
      projectName: '',
      environments: [],
      elements: [
        { id: 'e1', serviceType: 'lambda' as const, name: 'lambda-1', position: { x: 0, y: 0 }, config: {} },
        { id: 'e2', serviceType: 's3' as const, name: 's3-1', position: { x: 100, y: 0 }, config: {} },
      ],
      connectors: [
        { id: 'c1', sourceId: 'e1', targetId: 'e2', connectionType: 'triggers' },
      ],
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
    };

    useDiagramStore.getState().loadDiagramState(state);

    const conn = useDiagramStore.getState().connectors.get('c1');
    expect(conn).toBeDefined();
    expect(conn!.sourceId).toBe('e1');
    expect(conn!.targetId).toBe('e2');
  });

  it('restores viewport, projectName, and environments', () => {
    const state = {
      version: 1,
      projectName: 'my-proj',
      environments: [{ name: 'staging', variables: { region: 'eu-west-1' } }],
      elements: [],
      connectors: [],
      viewport: { offsetX: 100, offsetY: -50, scale: 1.5 },
    };

    useDiagramStore.getState().loadDiagramState(state);

    expect(useDiagramStore.getState().viewport).toEqual({ offsetX: 100, offsetY: -50, scale: 1.5 });
    expect(useDiagramStore.getState().projectName).toBe('my-proj');
    expect(useDiagramStore.getState().environments).toEqual([{ name: 'staging', variables: { region: 'eu-west-1' } }]);
  });

  it('clears undo/redo stacks on load', () => {
    // Build up some history
    useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    expect(useDiagramStore.getState().canUndo).toBe(true);

    const state = {
      version: 1,
      projectName: '',
      environments: [],
      elements: [],
      connectors: [],
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
    };

    useDiagramStore.getState().loadDiagramState(state);

    expect(useDiagramStore.getState().canUndo).toBe(false);
    expect(useDiagramStore.getState().canRedo).toBe(false);
    expect(useDiagramStore.getState()._undoStack).toHaveLength(0);
    expect(useDiagramStore.getState()._redoStack).toHaveLength(0);
  });

  it('deserializes canvasObjects from v2 state', () => {
    const state: Parameters<typeof useDiagramStore.getState>extends never ? never : {
      version: 2;
      projectName: string;
      environments: never[];
      elements: never[];
      connectors: never[];
      canvasObjects: {
        id: string;
        objectType: 'architecture-block';
        name: string;
        x: number;
        y: number;
        serviceType: 'lambda';
        config: { handler: string };
        visualConfig: { width: number; height: number };
      }[];
      viewport: { offsetX: number; offsetY: number; scale: number };
    } = {
      version: 2,
      projectName: 'v2-proj',
      environments: [],
      elements: [],
      connectors: [],
      canvasObjects: [
        {
          id: 'obj1',
          objectType: 'architecture-block',
          name: 'lambda-1',
          x: 10,
          y: 20,
          serviceType: 'lambda',
          config: { handler: 'index.handler' },
          visualConfig: { width: 100, height: 100 },
        },
      ],
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
    };

    useDiagramStore.getState().loadDiagramState(state as any);

    const obj = useDiagramStore.getState().canvasObjects.get('obj1');
    expect(obj).toBeDefined();
    expect(obj!.objectType).toBe('architecture-block');
    expect(obj!.name).toBe('lambda-1');
    if (obj!.objectType === 'architecture-block') {
      expect(obj!.position).toEqual({ x: 10, y: 20 });
      expect(obj!.serviceType).toBe('lambda');
      expect(obj!.visualConfig).toEqual({ width: 100, height: 100 });
    }
  });

  it('migrates v1 elements to canvasObjects with default visual configs', () => {
    const state = {
      version: 1,
      projectName: 'v1-proj',
      environments: [],
      elements: [
        { id: 'e1', serviceType: 'lambda' as const, name: 'lambda-1', position: { x: 50, y: 60 }, config: { handler: 'main.handler' } },
      ],
      connectors: [],
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
    };

    useDiagramStore.getState().loadDiagramState(state);

    const canvasObjects = useDiagramStore.getState().canvasObjects;
    expect(canvasObjects.size).toBe(1);

    const obj = canvasObjects.get('e1');
    expect(obj).toBeDefined();
    expect(obj!.objectType).toBe('architecture-block');
    if (obj!.objectType === 'architecture-block') {
      expect(obj!.position).toEqual({ x: 50, y: 60 });
      expect(obj!.serviceType).toBe('lambda');
      expect(obj!.config.handler).toBe('main.handler');
      expect(obj!.visualConfig).toEqual({ width: 80, height: 80 });
    }
  });

  it('handles missing canvasObjects in v2 state gracefully', () => {
    const state = {
      version: 2,
      projectName: 'v2-no-canvas',
      environments: [],
      elements: [
        { id: 'e1', serviceType: 'lambda' as const, name: 'lambda-1', position: { x: 0, y: 0 }, config: {} },
      ],
      connectors: [],
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
    };

    useDiagramStore.getState().loadDiagramState(state);

    // v2 with no canvasObjects should result in empty canvasObjects map (no migration)
    expect(useDiagramStore.getState().canvasObjects.size).toBe(0);
  });
});

describe('DiagramStore - serializeToArchitectureDescription', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      elements: new Map(),
      connectors: new Map(),
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
      projectName: '',
      environments: [],
      _undoStack: [],
      _redoStack: [],
      canUndo: false,
      canRedo: false,
    });
  });

  it('maps elements to resources with name, service_type, config', () => {
    const id = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    useDiagramStore.getState().updateElementConfig(id, { handler: 'app.handler', runtime: 'python3.12' });

    const desc = useDiagramStore.getState().serializeToArchitectureDescription();

    expect(desc.resources).toHaveLength(1);
    expect(desc.resources[0].name).toBe('lambda-1');
    expect(desc.resources[0].service_type).toBe('lambda');
    expect(desc.resources[0].config.handler).toBe('app.handler');
    expect(desc.resources[0].config.runtime).toBe('python3.12');
  });

  it('maps connectors to connections using element names', () => {
    const id1 = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    const id2 = useDiagramStore.getState().addElement('dynamodb', { x: 100, y: 0 });
    useDiagramStore.getState().addConnector(id1, id2, 'reads_from');

    const desc = useDiagramStore.getState().serializeToArchitectureDescription();

    expect(desc.connections).toHaveLength(1);
    expect(desc.connections[0].source).toBe('lambda-1');
    expect(desc.connections[0].target).toBe('dynamodb-1');
    expect(desc.connections[0].connection_type).toBe('reads_from');
  });

  it('includes project_name and environments', () => {
    useDiagramStore.getState().setProjectName('infra-project');
    useDiagramStore.getState().setEnvironments([
      { name: 'dev', variables: { region: 'us-east-1' } },
    ]);

    const desc = useDiagramStore.getState().serializeToArchitectureDescription();

    expect(desc.project_name).toBe('infra-project');
    expect(desc.environments).toEqual([{ name: 'dev', variables: { region: 'us-east-1' } }]);
  });

  it('returns empty resources and connections for empty diagram', () => {
    const desc = useDiagramStore.getState().serializeToArchitectureDescription();
    expect(desc.resources).toEqual([]);
    expect(desc.connections).toEqual([]);
  });
});
