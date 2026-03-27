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
      terraformVariables: {},
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

  it('maps elements to resources with name, service_type, config', () => {
    const id = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'lambda',
      name: 'lambda-1',
      position: { x: 0, y: 0 },
      config: { handler: 'app.handler', runtime: 'python3.12' },
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });

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

describe('DiagramStore - Object Grouping', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      elements: new Map(),
      connectors: new Map(),
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
      objectGroups: new Map(),
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
      _undoStack: [],
      _redoStack: [],
      canUndo: false,
      canRedo: false,
    });
  });

  function addTwoObjects(): [string, string] {
    const id1 = useDiagramStore.getState().addCanvasObject({
      objectType: 'geometric',
      name: 'rect-1',
      position: { x: 0, y: 0 },
      visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
    });
    const id2 = useDiagramStore.getState().addCanvasObject({
      objectType: 'geometric',
      name: 'rect-2',
      position: { x: 200, y: 0 },
      visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
    });
    return [id1, id2];
  }

  it('groupSelectedObjects returns null when fewer than 2 objects selected', () => {
    const [id1] = addTwoObjects();
    useDiagramStore.getState().selectObject(id1);
    const result = useDiagramStore.getState().groupSelectedObjects();
    expect(result).toBeNull();
    expect(useDiagramStore.getState().objectGroups.size).toBe(0);
  });

  it('groupSelectedObjects returns null when no objects selected', () => {
    addTwoObjects();
    const result = useDiagramStore.getState().groupSelectedObjects();
    expect(result).toBeNull();
  });

  it('groupSelectedObjects creates a group from 2+ selected objects', () => {
    const [id1, id2] = addTwoObjects();
    useDiagramStore.setState({ selectedObjectIds: new Set([id1, id2]) });

    const groupId = useDiagramStore.getState().groupSelectedObjects();
    expect(groupId).toBeTruthy();

    const group = useDiagramStore.getState().objectGroups.get(groupId!);
    expect(group).toBeDefined();
    expect(group!.memberIds).toContain(id1);
    expect(group!.memberIds).toContain(id2);
    expect(group!.memberIds).toHaveLength(2);
    expect(group!.name).toMatch(/^Group \d+$/);
  });

  it('groupSelectedObjects sets groupId on member objects', () => {
    const [id1, id2] = addTwoObjects();
    useDiagramStore.setState({ selectedObjectIds: new Set([id1, id2]) });

    const groupId = useDiagramStore.getState().groupSelectedObjects();

    const obj1 = useDiagramStore.getState().canvasObjects.get(id1)!;
    const obj2 = useDiagramStore.getState().canvasObjects.get(id2)!;
    expect(obj1.groupId).toBe(groupId);
    expect(obj2.groupId).toBe(groupId);
  });

  it('ungroupObjects dissolves the group and clears groupId on members', () => {
    const [id1, id2] = addTwoObjects();
    useDiagramStore.setState({ selectedObjectIds: new Set([id1, id2]) });

    const groupId = useDiagramStore.getState().groupSelectedObjects()!;
    useDiagramStore.getState().ungroupObjects(groupId);

    expect(useDiagramStore.getState().objectGroups.has(groupId)).toBe(false);
    expect(useDiagramStore.getState().canvasObjects.get(id1)!.groupId).toBeUndefined();
    expect(useDiagramStore.getState().canvasObjects.get(id2)!.groupId).toBeUndefined();
  });

  it('ungroupObjects is no-op for non-existent groupId', () => {
    const [id1, id2] = addTwoObjects();
    useDiagramStore.setState({ selectedObjectIds: new Set([id1, id2]) });
    useDiagramStore.getState().groupSelectedObjects();

    const sizeBefore = useDiagramStore.getState().objectGroups.size;
    useDiagramStore.getState().ungroupObjects('nonexistent');
    expect(useDiagramStore.getState().objectGroups.size).toBe(sizeBefore);
  });

  it('removeCanvasObject auto-dissolves group when fewer than 2 members remain', () => {
    const [id1, id2] = addTwoObjects();
    useDiagramStore.setState({ selectedObjectIds: new Set([id1, id2]) });

    const groupId = useDiagramStore.getState().groupSelectedObjects()!;
    expect(useDiagramStore.getState().objectGroups.size).toBe(1);

    // Remove one member — group should auto-dissolve since only 1 remains
    useDiagramStore.getState().removeCanvasObject(id1);

    expect(useDiagramStore.getState().objectGroups.has(groupId)).toBe(false);
    expect(useDiagramStore.getState().canvasObjects.get(id2)!.groupId).toBeUndefined();
  });

  it('removeCanvasObject keeps group intact when 2+ members remain', () => {
    const [id1, id2] = addTwoObjects();
    const id3 = useDiagramStore.getState().addCanvasObject({
      objectType: 'geometric',
      name: 'rect-3',
      position: { x: 400, y: 0 },
      visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
    });
    useDiagramStore.setState({ selectedObjectIds: new Set([id1, id2, id3]) });

    const groupId = useDiagramStore.getState().groupSelectedObjects()!;

    // Remove one member — group should still have 2 members
    useDiagramStore.getState().removeCanvasObject(id1);

    const group = useDiagramStore.getState().objectGroups.get(groupId);
    expect(group).toBeDefined();
    expect(group!.memberIds).toHaveLength(2);
    expect(group!.memberIds).toContain(id2);
    expect(group!.memberIds).toContain(id3);
  });

  it('groupSelectedObjects removes members from existing groups', () => {
    const [id1, id2] = addTwoObjects();
    const id3 = useDiagramStore.getState().addCanvasObject({
      objectType: 'geometric',
      name: 'rect-3',
      position: { x: 400, y: 0 },
      visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
    });

    // Group id1 and id2
    useDiagramStore.setState({ selectedObjectIds: new Set([id1, id2]) });
    const group1Id = useDiagramStore.getState().groupSelectedObjects()!;

    // Now group id2 and id3 — id2 should be removed from group1
    useDiagramStore.setState({ selectedObjectIds: new Set([id2, id3]) });
    const group2Id = useDiagramStore.getState().groupSelectedObjects()!;

    // group1 should be auto-dissolved (only id1 left)
    expect(useDiagramStore.getState().objectGroups.has(group1Id)).toBe(false);
    expect(useDiagramStore.getState().canvasObjects.get(id1)!.groupId).toBeUndefined();

    // group2 should exist with id2 and id3
    const group2 = useDiagramStore.getState().objectGroups.get(group2Id);
    expect(group2).toBeDefined();
    expect(group2!.memberIds).toContain(id2);
    expect(group2!.memberIds).toContain(id3);
    expect(useDiagramStore.getState().canvasObjects.get(id2)!.groupId).toBe(group2Id);
  });

  it('loadDiagramState resets objectGroups', () => {
    const [id1, id2] = addTwoObjects();
    useDiagramStore.setState({ selectedObjectIds: new Set([id1, id2]) });
    useDiagramStore.getState().groupSelectedObjects();
    expect(useDiagramStore.getState().objectGroups.size).toBe(1);

    useDiagramStore.getState().loadDiagramState({
      version: 2,
      projectName: '',
      environments: [],
      elements: [],
      connectors: [],
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
    });

    expect(useDiagramStore.getState().objectGroups.size).toBe(0);
  });

  it('selectObject selects all group members when clicking a grouped object', () => {
    const [id1, id2] = addTwoObjects();
    useDiagramStore.setState({ selectedObjectIds: new Set([id1, id2]) });
    const groupId = useDiagramStore.getState().groupSelectedObjects()!;
    expect(groupId).toBeTruthy();

    // Clear selection, then select just one member
    useDiagramStore.getState().clearSelection();
    expect(useDiagramStore.getState().selectedObjectIds.size).toBe(0);

    useDiagramStore.getState().selectObject(id1);

    // Both group members should be selected
    const selected = useDiagramStore.getState().selectedObjectIds;
    expect(selected.size).toBe(2);
    expect(selected.has(id1)).toBe(true);
    expect(selected.has(id2)).toBe(true);
  });

  it('selectObject selects only the clicked object when it has no group', () => {
    const [id1, id2] = addTwoObjects();

    useDiagramStore.getState().selectObject(id1);

    const selected = useDiagramStore.getState().selectedObjectIds;
    expect(selected.size).toBe(1);
    expect(selected.has(id1)).toBe(true);
    expect(selected.has(id2)).toBe(false);
  });

  it('selectObject with null clears the selection', () => {
    const [id1] = addTwoObjects();
    useDiagramStore.getState().selectObject(id1);
    expect(useDiagramStore.getState().selectedObjectIds.size).toBe(1);

    useDiagramStore.getState().selectObject(null);
    expect(useDiagramStore.getState().selectedObjectIds.size).toBe(0);
  });
});

describe('DiagramStore - moveSelectedObjects', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      elements: new Map(),
      connectors: new Map(),
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
      objectGroups: new Map(),
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
      _undoStack: [],
      _redoStack: [],
      canUndo: false,
      canRedo: false,
    });
  });

  it('moves a single selected architecture-block by offset', () => {
    const id = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'lambda',
      name: 'lambda-1',
      position: { x: 100, y: 200 },
      config: {},
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });
    useDiagramStore.getState().selectObject(id);
    useDiagramStore.getState().moveSelectedObjects(10, -20);

    const obj = useDiagramStore.getState().canvasObjects.get(id)!;
    expect(obj.objectType === 'architecture-block' && obj.position).toEqual({ x: 110, y: 180 });
  });

  it('moves a single selected geometric object by offset', () => {
    const id = useDiagramStore.getState().addCanvasObject({
      objectType: 'geometric',
      name: 'rect-1',
      position: { x: 50, y: 50 },
      visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
    });
    useDiagramStore.getState().selectObject(id);
    useDiagramStore.getState().moveSelectedObjects(5, 15);

    const obj = useDiagramStore.getState().canvasObjects.get(id)!;
    expect(obj.objectType === 'geometric' && obj.position).toEqual({ x: 55, y: 65 });
  });

  it('moves a line object by updating both start and end points', () => {
    const id = useDiagramStore.getState().addCanvasObject({
      objectType: 'line',
      name: 'line-1',
      start: { x: 10, y: 20 },
      end: { x: 100, y: 200 },
      visualConfig: { color: '#fff', borderWidth: 2, strokeStyle: 'solid', startArrow: false, endArrow: false },
    });
    useDiagramStore.getState().selectObject(id);
    useDiagramStore.getState().moveSelectedObjects(5, -5);

    const obj = useDiagramStore.getState().canvasObjects.get(id)!;
    if (obj.objectType === 'line') {
      expect(obj.start).toEqual({ x: 15, y: 15 });
      expect(obj.end).toEqual({ x: 105, y: 195 });
    }
  });

  it('moves multiple selected objects by the same offset', () => {
    const id1 = useDiagramStore.getState().addCanvasObject({
      objectType: 'geometric',
      name: 'rect-1',
      position: { x: 0, y: 0 },
      visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
    });
    const id2 = useDiagramStore.getState().addCanvasObject({
      objectType: 'geometric',
      name: 'rect-2',
      position: { x: 200, y: 200 },
      visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
    });
    useDiagramStore.setState({ selectedObjectIds: new Set([id1, id2]) });
    useDiagramStore.getState().moveSelectedObjects(10, 10);

    const obj1 = useDiagramStore.getState().canvasObjects.get(id1)!;
    const obj2 = useDiagramStore.getState().canvasObjects.get(id2)!;
    expect(obj1.objectType === 'geometric' && obj1.position).toEqual({ x: 10, y: 10 });
    expect(obj2.objectType === 'geometric' && obj2.position).toEqual({ x: 210, y: 210 });
  });

  it('moves all group members when one grouped object is selected', () => {
    const id1 = useDiagramStore.getState().addCanvasObject({
      objectType: 'geometric',
      name: 'rect-1',
      position: { x: 0, y: 0 },
      visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
    });
    const id2 = useDiagramStore.getState().addCanvasObject({
      objectType: 'geometric',
      name: 'rect-2',
      position: { x: 200, y: 0 },
      visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
    });

    // Group them
    useDiagramStore.setState({ selectedObjectIds: new Set([id1, id2]) });
    useDiagramStore.getState().groupSelectedObjects();

    // Select only id1, but id2 should also move because they're grouped
    useDiagramStore.getState().selectObject(id1);
    useDiagramStore.getState().moveSelectedObjects(30, 40);

    const obj1 = useDiagramStore.getState().canvasObjects.get(id1)!;
    const obj2 = useDiagramStore.getState().canvasObjects.get(id2)!;
    expect(obj1.objectType === 'geometric' && obj1.position).toEqual({ x: 30, y: 40 });
    expect(obj2.objectType === 'geometric' && obj2.position).toEqual({ x: 230, y: 40 });
  });

  it('is no-op when selection is empty', () => {
    const id = useDiagramStore.getState().addCanvasObject({
      objectType: 'geometric',
      name: 'rect-1',
      position: { x: 50, y: 50 },
      visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
    });
    useDiagramStore.getState().moveSelectedObjects(10, 10);

    const obj = useDiagramStore.getState().canvasObjects.get(id)!;
    expect(obj.objectType === 'geometric' && obj.position).toEqual({ x: 50, y: 50 });
  });

  it('does not move unselected non-grouped objects', () => {
    const id1 = useDiagramStore.getState().addCanvasObject({
      objectType: 'geometric',
      name: 'rect-1',
      position: { x: 0, y: 0 },
      visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
    });
    const id2 = useDiagramStore.getState().addCanvasObject({
      objectType: 'geometric',
      name: 'rect-2',
      position: { x: 200, y: 200 },
      visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
    });

    // Select only id1
    useDiagramStore.getState().selectObject(id1);
    useDiagramStore.getState().moveSelectedObjects(10, 10);

    const obj2 = useDiagramStore.getState().canvasObjects.get(id2)!;
    expect(obj2.objectType === 'geometric' && obj2.position).toEqual({ x: 200, y: 200 });
  });
});

describe('DiagramStore - Serialization of zIndex, groupId, and objectGroups', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      elements: new Map(),
      connectors: new Map(),
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
      objectGroups: new Map(),
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
      projectName: '',
      environments: [],
      _undoStack: [],
      _redoStack: [],
      canUndo: false,
      canRedo: false,
    });
  });

  it('serializeDiagramState includes zIndex on each canvas object', () => {
    const id = useDiagramStore.getState().addCanvasObject({
      objectType: 'geometric',
      name: 'rect-1',
      position: { x: 10, y: 20 },
      visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
    });

    const state = useDiagramStore.getState().serializeDiagramState();
    const sObj = state.canvasObjects!.find((o) => o.id === id)!;
    expect(sObj.zIndex).toBe(0);
  });

  it('serializeDiagramState includes groupId on grouped canvas objects', () => {
    const id1 = useDiagramStore.getState().addCanvasObject({
      objectType: 'geometric',
      name: 'rect-1',
      position: { x: 0, y: 0 },
      visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
    });
    const id2 = useDiagramStore.getState().addCanvasObject({
      objectType: 'geometric',
      name: 'rect-2',
      position: { x: 200, y: 0 },
      visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
    });

    useDiagramStore.setState({ selectedObjectIds: new Set([id1, id2]) });
    const groupId = useDiagramStore.getState().groupSelectedObjects()!;

    const state = useDiagramStore.getState().serializeDiagramState();
    const sObj1 = state.canvasObjects!.find((o) => o.id === id1)!;
    const sObj2 = state.canvasObjects!.find((o) => o.id === id2)!;
    expect(sObj1.groupId).toBe(groupId);
    expect(sObj2.groupId).toBe(groupId);
  });

  it('serializeDiagramState does not include groupId on ungrouped objects', () => {
    useDiagramStore.getState().addCanvasObject({
      objectType: 'geometric',
      name: 'rect-1',
      position: { x: 0, y: 0 },
      visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
    });

    const state = useDiagramStore.getState().serializeDiagramState();
    expect(state.canvasObjects![0].groupId).toBeUndefined();
  });

  it('serializeDiagramState includes objectGroups when groups exist', () => {
    const id1 = useDiagramStore.getState().addCanvasObject({
      objectType: 'geometric',
      name: 'rect-1',
      position: { x: 0, y: 0 },
      visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
    });
    const id2 = useDiagramStore.getState().addCanvasObject({
      objectType: 'geometric',
      name: 'rect-2',
      position: { x: 200, y: 0 },
      visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
    });

    useDiagramStore.setState({ selectedObjectIds: new Set([id1, id2]) });
    const groupId = useDiagramStore.getState().groupSelectedObjects()!;

    const state = useDiagramStore.getState().serializeDiagramState();
    expect(state.objectGroups).toBeDefined();
    expect(state.objectGroups).toHaveLength(1);
    expect(state.objectGroups![0].id).toBe(groupId);
    expect(state.objectGroups![0].memberIds).toContain(id1);
    expect(state.objectGroups![0].memberIds).toContain(id2);
  });

  it('serializeDiagramState omits objectGroups when no groups exist', () => {
    useDiagramStore.getState().addCanvasObject({
      objectType: 'geometric',
      name: 'rect-1',
      position: { x: 0, y: 0 },
      visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
    });

    const state = useDiagramStore.getState().serializeDiagramState();
    expect(state.objectGroups).toBeUndefined();
  });

  it('loadDiagramState deserializes zIndex from serialized state', () => {
    const state = useDiagramStore.getState().serializeDiagramState();

    // Create objects with specific zIndex values
    const id1 = useDiagramStore.getState().addCanvasObject({
      objectType: 'geometric',
      name: 'rect-1',
      position: { x: 0, y: 0 },
      visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
    });
    const id2 = useDiagramStore.getState().addCanvasObject({
      objectType: 'geometric',
      name: 'rect-2',
      position: { x: 200, y: 0 },
      visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
    });

    // Bring id1 to front so it has a higher zIndex
    useDiagramStore.getState().bringToFront(id1);

    const serialized = useDiagramStore.getState().serializeDiagramState();
    useDiagramStore.getState().loadDiagramState(serialized);

    const obj1 = useDiagramStore.getState().canvasObjects.get(id1)!;
    const obj2 = useDiagramStore.getState().canvasObjects.get(id2)!;
    expect(obj1.zIndex).toBeGreaterThan(obj2.zIndex);
  });

  it('loadDiagramState defaults zIndex to insertion index when missing', () => {
    const serialized = {
      version: 2,
      projectName: '',
      environments: [],
      elements: [],
      connectors: [],
      canvasObjects: [
        {
          id: 'a',
          objectType: 'geometric' as const,
          name: 'rect-1',
          x: 0,
          y: 0,
          visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
        },
        {
          id: 'b',
          objectType: 'geometric' as const,
          name: 'rect-2',
          x: 200,
          y: 0,
          visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
        },
      ],
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
    };

    useDiagramStore.getState().loadDiagramState(serialized as any);

    expect(useDiagramStore.getState().canvasObjects.get('a')!.zIndex).toBe(0);
    expect(useDiagramStore.getState().canvasObjects.get('b')!.zIndex).toBe(1);
  });

  it('loadDiagramState deserializes objectGroups and restores groupId on objects', () => {
    const serialized = {
      version: 2,
      projectName: '',
      environments: [],
      elements: [],
      connectors: [],
      canvasObjects: [
        {
          id: 'a',
          objectType: 'geometric' as const,
          name: 'rect-1',
          x: 0,
          y: 0,
          visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
          zIndex: 0,
          groupId: 'g1',
        },
        {
          id: 'b',
          objectType: 'geometric' as const,
          name: 'rect-2',
          x: 200,
          y: 0,
          visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
          zIndex: 1,
          groupId: 'g1',
        },
      ],
      objectGroups: [
        { id: 'g1', name: 'Group 1', memberIds: ['a', 'b'] },
      ],
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
    };

    useDiagramStore.getState().loadDiagramState(serialized as any);

    // Verify objectGroups are restored
    expect(useDiagramStore.getState().objectGroups.size).toBe(1);
    const group = useDiagramStore.getState().objectGroups.get('g1')!;
    expect(group.name).toBe('Group 1');
    expect(group.memberIds).toEqual(['a', 'b']);

    // Verify groupId is restored on objects
    expect(useDiagramStore.getState().canvasObjects.get('a')!.groupId).toBe('g1');
    expect(useDiagramStore.getState().canvasObjects.get('b')!.groupId).toBe('g1');
  });

  it('loadDiagramState defaults objectGroups to empty when missing', () => {
    const serialized = {
      version: 2,
      projectName: '',
      environments: [],
      elements: [],
      connectors: [],
      canvasObjects: [],
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
    };

    useDiagramStore.getState().loadDiagramState(serialized as any);
    expect(useDiagramStore.getState().objectGroups.size).toBe(0);
  });

  it('round-trip: serialize then load preserves zIndex, groupId, and objectGroups', () => {
    const id1 = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'lambda',
      name: 'lambda-1',
      position: { x: 10, y: 20 },
      config: {},
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });
    const id2 = useDiagramStore.getState().addCanvasObject({
      objectType: 'geometric',
      name: 'rect-1',
      position: { x: 200, y: 0 },
      visualConfig: { width: 100, height: 100, fill: true, fillColor: '#fff', borderColor: '#000', borderWidth: 2, shape: 'rectangle' },
    });

    // Group them
    useDiagramStore.setState({ selectedObjectIds: new Set([id1, id2]) });
    const groupId = useDiagramStore.getState().groupSelectedObjects()!;

    // Bring id2 to front
    useDiagramStore.getState().bringToFront(id2);

    const beforeObj1 = useDiagramStore.getState().canvasObjects.get(id1)!;
    const beforeObj2 = useDiagramStore.getState().canvasObjects.get(id2)!;

    // Serialize and reload
    const serialized = useDiagramStore.getState().serializeDiagramState();
    useDiagramStore.getState().loadDiagramState(serialized);

    const afterObj1 = useDiagramStore.getState().canvasObjects.get(id1)!;
    const afterObj2 = useDiagramStore.getState().canvasObjects.get(id2)!;

    // zIndex preserved
    expect(afterObj1.zIndex).toBe(beforeObj1.zIndex);
    expect(afterObj2.zIndex).toBe(beforeObj2.zIndex);

    // groupId preserved
    expect(afterObj1.groupId).toBe(groupId);
    expect(afterObj2.groupId).toBe(groupId);

    // objectGroups preserved
    expect(useDiagramStore.getState().objectGroups.size).toBe(1);
    const group = useDiagramStore.getState().objectGroups.get(groupId)!;
    expect(group.memberIds).toContain(id1);
    expect(group.memberIds).toContain(id2);
  });
});
