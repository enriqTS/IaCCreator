import { describe, it, expect, beforeEach } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';
import type { ArchitectureBlock } from '@/types/diagram';

function resetStore() {
  useDiagramStore.setState({
    connectors: new Map(),
    canvasObjects: new Map(),
    selectedObjectIds: new Set(),
    objectGroups: new Map(),
    viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
    activeTool: 'pointer',
    selectedConnectorId: null,
    pendingConnectorSourceId: null,
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
    projectName: '',
    environments: [],
  });
}

function addBlock(serviceType: string, position: { x: number; y: number }, name?: string): string {
  return useDiagramStore.getState().addCanvasObject({
    objectType: 'architecture-block',
    serviceType: serviceType as import('@/types/diagram').ServiceType,
    name: name || `${serviceType}-block`,
    position,
    config: {},
    terraformVariables: {},
    visualConfig: { width: 80, height: 80 },
  });
}

describe('DiagramStore - Connector Operations', () => {
  beforeEach(resetStore);

  it('addConnector creates connector with default connectionType "triggers"', () => {
    const id1 = addBlock('lambda', { x: 0, y: 0 });
    const id2 = addBlock('s3', { x: 100, y: 0 });

    const cid = useDiagramStore.getState().addConnector(id1, id2);
    const conn = useDiagramStore.getState().connectors.get(cid)!;

    expect(conn.sourceId).toBe(id1);
    expect(conn.targetId).toBe(id2);
    expect(conn.connectionType).toBe('triggers');
  });

  it('addConnector uses provided connectionType', () => {
    const id1 = addBlock('lambda', { x: 0, y: 0 });
    const id2 = addBlock('dynamodb', { x: 100, y: 0 });

    const cid = useDiagramStore.getState().addConnector(id1, id2, 'reads_from');
    expect(useDiagramStore.getState().connectors.get(cid)!.connectionType).toBe('reads_from');
  });

  it('addConnector rejects self-connections', () => {
    const id = addBlock('lambda', { x: 0, y: 0 });
    expect(() => useDiagramStore.getState().addConnector(id, id)).toThrow();
  });

  it('addConnector rejects non-existent source', () => {
    const id = addBlock('lambda', { x: 0, y: 0 });
    expect(() => useDiagramStore.getState().addConnector('nonexistent', id)).toThrow();
  });

  it('addConnector rejects non-existent target', () => {
    const id = addBlock('lambda', { x: 0, y: 0 });
    expect(() => useDiagramStore.getState().addConnector(id, 'nonexistent')).toThrow();
  });

  it('updateConnectorType changes the connectionType', () => {
    const id1 = addBlock('lambda', { x: 0, y: 0 });
    const id2 = addBlock('s3', { x: 100, y: 0 });
    const cid = useDiagramStore.getState().addConnector(id1, id2);

    useDiagramStore.getState().updateConnectorType(cid, 'writes_to');
    expect(useDiagramStore.getState().connectors.get(cid)!.connectionType).toBe('writes_to');
  });

  it('removeConnector deletes only the connector', () => {
    const id1 = addBlock('lambda', { x: 0, y: 0 });
    const id2 = addBlock('s3', { x: 100, y: 0 });
    const cid = useDiagramStore.getState().addConnector(id1, id2);

    useDiagramStore.getState().removeConnector(cid);

    expect(useDiagramStore.getState().connectors.has(cid)).toBe(false);
    // Canvas objects should remain
    expect(useDiagramStore.getState().canvasObjects.has(id1)).toBe(true);
    expect(useDiagramStore.getState().canvasObjects.has(id2)).toBe(true);
  });
});

describe('DiagramStore - Connector Config Management', () => {
  beforeEach(resetStore);

  it('updateConnectorConfig sets a single key in connectionConfig', () => {
    const id1 = addBlock('lambda', { x: 0, y: 0 });
    const id2 = addBlock('s3', { x: 100, y: 0 });
    const cid = useDiagramStore.getState().addConnector(id1, id2);

    useDiagramStore.getState().updateConnectorConfig(cid, 'access_pattern', 'read');

    const conn = useDiagramStore.getState().connectors.get(cid)!;
    expect(conn.connectionConfig).toEqual({ access_pattern: 'read' });
  });

  it('updateConnectorConfig preserves existing config keys', () => {
    const id1 = addBlock('lambda', { x: 0, y: 0 });
    const id2 = addBlock('s3', { x: 100, y: 0 });
    const cid = useDiagramStore.getState().addConnector(id1, id2);

    useDiagramStore.getState().updateConnectorConfig(cid, 'connection_role', 'route_handler');
    useDiagramStore.getState().updateConnectorConfig(cid, 'http_method', 'GET');

    const conn = useDiagramStore.getState().connectors.get(cid)!;
    expect(conn.connectionConfig).toEqual({ connection_role: 'route_handler', http_method: 'GET' });
  });

  it('updateConnectorConfig overwrites an existing key', () => {
    const id1 = addBlock('lambda', { x: 0, y: 0 });
    const id2 = addBlock('s3', { x: 100, y: 0 });
    const cid = useDiagramStore.getState().addConnector(id1, id2);

    useDiagramStore.getState().updateConnectorConfig(cid, 'batch_size', 10);
    useDiagramStore.getState().updateConnectorConfig(cid, 'batch_size', 50);

    const conn = useDiagramStore.getState().connectors.get(cid)!;
    expect(conn.connectionConfig!.batch_size).toBe(50);
  });

  it('updateConnectorConfig is no-op for non-existent connector', () => {
    const before = new Map(useDiagramStore.getState().connectors);
    useDiagramStore.getState().updateConnectorConfig('nonexistent', 'key', 'value');
    expect(useDiagramStore.getState().connectors).toEqual(before);
  });

  it('updateConnectorConfig pushes history for undo support', () => {
    const id1 = addBlock('lambda', { x: 0, y: 0 });
    const id2 = addBlock('s3', { x: 100, y: 0 });
    const cid = useDiagramStore.getState().addConnector(id1, id2);

    useDiagramStore.getState().updateConnectorConfig(cid, 'access_pattern', 'write');

    expect(useDiagramStore.getState().canUndo).toBe(true);
    useDiagramStore.getState().undo();

    const conn = useDiagramStore.getState().connectors.get(cid)!;
    expect(conn.connectionConfig).toBeUndefined();
  });

  it('removeConnectorConfigKeys removes specified keys', () => {
    const id1 = addBlock('lambda', { x: 0, y: 0 });
    const id2 = addBlock('s3', { x: 100, y: 0 });
    const cid = useDiagramStore.getState().addConnector(id1, id2);

    useDiagramStore.getState().updateConnectorConfig(cid, 'connection_role', 'route_handler');
    useDiagramStore.getState().updateConnectorConfig(cid, 'http_method', 'GET');
    useDiagramStore.getState().updateConnectorConfig(cid, 'route_path', '/users');

    useDiagramStore.getState().removeConnectorConfigKeys(cid, ['http_method', 'route_path']);

    const conn = useDiagramStore.getState().connectors.get(cid)!;
    expect(conn.connectionConfig).toEqual({ connection_role: 'route_handler' });
  });

  it('removeConnectorConfigKeys pushes history for undo support', () => {
    const id1 = addBlock('lambda', { x: 0, y: 0 });
    const id2 = addBlock('s3', { x: 100, y: 0 });
    const cid = useDiagramStore.getState().addConnector(id1, id2);

    useDiagramStore.getState().updateConnectorConfig(cid, 'http_method', 'POST');
    useDiagramStore.getState().removeConnectorConfigKeys(cid, ['http_method']);

    expect(useDiagramStore.getState().connectors.get(cid)!.connectionConfig).toEqual({});

    useDiagramStore.getState().undo();
    expect(useDiagramStore.getState().connectors.get(cid)!.connectionConfig).toEqual({ http_method: 'POST' });
  });

  it('updateConnectorConfigBatch sets multiple keys at once', () => {
    const id1 = addBlock('lambda', { x: 0, y: 0 });
    const id2 = addBlock('s3', { x: 100, y: 0 });
    const cid = useDiagramStore.getState().addConnector(id1, id2);

    useDiagramStore.getState().updateConnectorConfigBatch(cid, {
      connection_role: 'route_handler',
      http_method: 'POST',
      route_path: '/api/users',
    });

    const conn = useDiagramStore.getState().connectors.get(cid)!;
    expect(conn.connectionConfig).toEqual({
      connection_role: 'route_handler',
      http_method: 'POST',
      route_path: '/api/users',
    });
  });

  it('updateConnectorConfigBatch pushes history for undo support', () => {
    const id1 = addBlock('lambda', { x: 0, y: 0 });
    const id2 = addBlock('s3', { x: 100, y: 0 });
    const cid = useDiagramStore.getState().addConnector(id1, id2);

    useDiagramStore.getState().updateConnectorConfigBatch(cid, { batch_size: 100, maximum_batching_window_in_seconds: 60 });

    expect(useDiagramStore.getState().canUndo).toBe(true);
    useDiagramStore.getState().undo();

    const conn = useDiagramStore.getState().connectors.get(cid)!;
    expect(conn.connectionConfig).toBeUndefined();
  });
});

describe('DiagramStore - Viewport State', () => {
  beforeEach(resetStore);

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
  beforeEach(resetStore);

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

  it('selectConnector sets selectedConnectorId', () => {
    useDiagramStore.getState().selectConnector('conn-1');
    expect(useDiagramStore.getState().selectedConnectorId).toBe('conn-1');
  });

  it('selectConnector with null deselects', () => {
    useDiagramStore.setState({ selectedConnectorId: 'conn-1' });
    useDiagramStore.getState().selectConnector(null);
    expect(useDiagramStore.getState().selectedConnectorId).toBeNull();
  });
});

describe('DiagramStore - Undo/Redo', () => {
  beforeEach(resetStore);

  it('canUndo is false initially', () => {
    expect(useDiagramStore.getState().canUndo).toBe(false);
  });

  it('canRedo is false initially', () => {
    expect(useDiagramStore.getState().canRedo).toBe(false);
  });

  it('addCanvasObject makes canUndo true', () => {
    addBlock('lambda', { x: 0, y: 0 });
    expect(useDiagramStore.getState().canUndo).toBe(true);
  });

  it('undo after addCanvasObject restores empty state', () => {
    addBlock('lambda', { x: 0, y: 0 });
    expect(useDiagramStore.getState().canvasObjects.size).toBe(1);

    useDiagramStore.getState().undo();
    expect(useDiagramStore.getState().canvasObjects.size).toBe(0);
    expect(useDiagramStore.getState().canUndo).toBe(false);
    expect(useDiagramStore.getState().canRedo).toBe(true);
  });

  it('redo after undo restores the canvas object', () => {
    addBlock('lambda', { x: 10, y: 20 });
    useDiagramStore.getState().undo();
    expect(useDiagramStore.getState().canvasObjects.size).toBe(0);

    useDiagramStore.getState().redo();
    expect(useDiagramStore.getState().canvasObjects.size).toBe(1);
    const obj = Array.from(useDiagramStore.getState().canvasObjects.values())[0];
    expect(obj.objectType).toBe('architecture-block');
  });

  it('new mutation clears redo stack', () => {
    addBlock('lambda', { x: 0, y: 0 });
    useDiagramStore.getState().undo();
    expect(useDiagramStore.getState().canRedo).toBe(true);

    addBlock('s3', { x: 50, y: 50 });
    expect(useDiagramStore.getState().canRedo).toBe(false);
  });

  it('undo is no-op when stack is empty', () => {
    const sizeBefore = useDiagramStore.getState().canvasObjects.size;
    useDiagramStore.getState().undo();
    expect(useDiagramStore.getState().canvasObjects.size).toBe(sizeBefore);
  });

  it('redo is no-op when stack is empty', () => {
    const sizeBefore = useDiagramStore.getState().canvasObjects.size;
    useDiagramStore.getState().redo();
    expect(useDiagramStore.getState().canvasObjects.size).toBe(sizeBefore);
  });
});

describe('DiagramStore - Project State', () => {
  beforeEach(resetStore);

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
  beforeEach(resetStore);

  it('returns DiagramState with version 3', () => {
    const state = useDiagramStore.getState().serializeDiagramState();
    expect(state.version).toBe(3);
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
});

describe('DiagramStore - loadDiagramState', () => {
  beforeEach(resetStore);

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
    addBlock('lambda', { x: 0, y: 0 });
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
  });

  it('deserializes canvasObjects from v2 state', () => {
    const state = {
      version: 2,
      projectName: 'v2-proj',
      environments: [],
      elements: [],
      connectors: [],
      canvasObjects: [
        {
          id: 'obj1',
          objectType: 'architecture-block' as const,
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

  it('discards legacy elements field when loading saved diagram (requirement 2.4)', () => {
    const state = {
      version: 2,
      projectName: 'test',
      environments: [],
      elements: [
        { id: 'legacy-el', serviceType: 'lambda' as const, name: 'old-lambda', position: { x: 0, y: 0 }, config: {} },
      ],
      connectors: [],
      canvasObjects: [
        {
          id: 'obj1',
          objectType: 'architecture-block' as const,
          name: 'new-lambda',
          x: 10,
          y: 20,
          serviceType: 'lambda',
          config: {},
          visualConfig: { width: 80, height: 80 },
        },
      ],
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
    };

    // Should not throw
    useDiagramStore.getState().loadDiagramState(state as any);

    // Canvas objects should be loaded normally
    expect(useDiagramStore.getState().canvasObjects.size).toBe(1);
    expect(useDiagramStore.getState().canvasObjects.get('obj1')).toBeDefined();
  });
});

describe('DiagramStore - serializeToArchitectureDescription', () => {
  beforeEach(resetStore);

  it('maps canvas objects to resources with name, service_type, config', () => {
    useDiagramStore.getState().addCanvasObject({
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

  it('maps connectors to connections using canvas object names', () => {
    const id1 = addBlock('lambda', { x: 0, y: 0 }, 'lambda-1');
    const id2 = addBlock('dynamodb', { x: 100, y: 0 }, 'dynamodb-1');
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
