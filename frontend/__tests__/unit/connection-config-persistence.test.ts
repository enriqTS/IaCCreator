import { describe, it, expect, beforeEach } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';

function resetStore() {
  useDiagramStore.setState({
    elements: new Map(),
    connectors: new Map(),
    canvasObjects: new Map(),
    objectGroups: new Map(),
    viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
    projectName: 'test-project',
    environments: [],
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
}

function addTwoBlocks() {
  const sourceId = useDiagramStore.getState().addCanvasObject({
    objectType: 'architecture-block',
    serviceType: 'api-gateway',
    name: 'my-api',
    position: { x: 0, y: 0 },
    config: {},
    terraformVariables: {},
    visualConfig: { width: 80, height: 80 },
  });
  const targetId = useDiagramStore.getState().addCanvasObject({
    objectType: 'architecture-block',
    serviceType: 'lambda',
    name: 'my-lambda',
    position: { x: 200, y: 0 },
    config: {},
    terraformVariables: {},
    visualConfig: { width: 80, height: 80 },
  });
  return { sourceId, targetId };
}

describe('Connection Config Persistence - serializeDiagramState', () => {
  beforeEach(() => {
    resetStore();
  });

  it('serializes connectionConfig with connection_role, http_method, route_path correctly', () => {
    const { sourceId, targetId } = addTwoBlocks();
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    useDiagramStore.getState().updateConnectorConfigBatch(connectorId, {
      connection_role: 'route_handler',
      http_method: 'GET',
      route_path: '/users',
    });

    const serialized = useDiagramStore.getState().serializeDiagramState();
    const serializedConnector = serialized.connectors.find((c) => c.id === connectorId)!;

    expect(serializedConnector.connection_config).toEqual({
      connection_role: 'route_handler',
      http_method: 'GET',
      route_path: '/users',
    });
  });

  it('serializes connectionConfig with access_pattern correctly', () => {
    const sourceId = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'lambda',
      name: 'my-lambda',
      position: { x: 0, y: 0 },
      config: {},
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });
    const targetId = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'dynamodb',
      name: 'my-table',
      position: { x: 200, y: 0 },
      config: {},
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    useDiagramStore.getState().updateConnectorConfig(connectorId, 'access_pattern', 'read');

    const serialized = useDiagramStore.getState().serializeDiagramState();
    const serializedConnector = serialized.connectors.find((c) => c.id === connectorId)!;

    expect(serializedConnector.connection_config).toEqual({ access_pattern: 'read' });
  });

  it('serializes connectionConfig with batch_size correctly', () => {
    const sourceId = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'sqs',
      name: 'my-queue',
      position: { x: 0, y: 0 },
      config: {},
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });
    const targetId = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'lambda',
      name: 'my-lambda',
      position: { x: 200, y: 0 },
      config: {},
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    useDiagramStore.getState().updateConnectorConfigBatch(connectorId, {
      batch_size: 50,
      maximum_batching_window_in_seconds: 10,
    });

    const serialized = useDiagramStore.getState().serializeDiagramState();
    const serializedConnector = serialized.connectors.find((c) => c.id === connectorId)!;

    expect(serializedConnector.connection_config).toEqual({
      batch_size: 50,
      maximum_batching_window_in_seconds: 10,
    });
  });

  it('omits connection_config when connectionConfig is undefined', () => {
    const { sourceId, targetId } = addTwoBlocks();
    useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');

    const serialized = useDiagramStore.getState().serializeDiagramState();
    const serializedConnector = serialized.connectors[0];

    expect(serializedConnector.connection_config).toBeUndefined();
  });

  it('serializes empty connectionConfig as empty object (not undefined)', () => {
    const { sourceId, targetId } = addTwoBlocks();
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    // Set connectionConfig to an empty object explicitly
    useDiagramStore.setState((state) => {
      const next = new Map(state.connectors);
      const connector = next.get(connectorId)!;
      next.set(connectorId, { ...connector, connectionConfig: {} });
      return { connectors: next };
    });

    const serialized = useDiagramStore.getState().serializeDiagramState();
    const serializedConnector = serialized.connectors.find((c) => c.id === connectorId)!;

    expect(serializedConnector.connection_config).toEqual({});
  });
});

describe('Connection Config Persistence - loadDiagramState', () => {
  beforeEach(() => {
    resetStore();
  });

  it('restores connection_config with new keys correctly', () => {
    const { sourceId, targetId } = addTwoBlocks();
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    useDiagramStore.getState().updateConnectorConfigBatch(connectorId, {
      connection_role: 'route_handler',
      http_method: 'POST',
      route_path: '/items/{id}',
    });

    const serialized = useDiagramStore.getState().serializeDiagramState();
    resetStore();
    useDiagramStore.getState().loadDiagramState(serialized);

    const restored = useDiagramStore.getState().connectors.get(connectorId)!;
    expect(restored.connectionConfig).toEqual({
      connection_role: 'route_handler',
      http_method: 'POST',
      route_path: '/items/{id}',
    });
  });

  it('restores access_pattern from connection_config', () => {
    const sourceId = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'lambda',
      name: 'fn',
      position: { x: 0, y: 0 },
      config: {},
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });
    const targetId = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 's3',
      name: 'bucket',
      position: { x: 200, y: 0 },
      config: {},
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    useDiagramStore.getState().updateConnectorConfig(connectorId, 'access_pattern', 'write');

    const serialized = useDiagramStore.getState().serializeDiagramState();
    resetStore();
    useDiagramStore.getState().loadDiagramState(serialized);

    const restored = useDiagramStore.getState().connectors.get(connectorId)!;
    expect(restored.connectionConfig).toEqual({ access_pattern: 'write' });
  });

  it('restores batch_size and maximum_batching_window_in_seconds from connection_config', () => {
    const sourceId = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'sqs',
      name: 'queue',
      position: { x: 0, y: 0 },
      config: {},
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });
    const targetId = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'lambda',
      name: 'fn',
      position: { x: 200, y: 0 },
      config: {},
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    useDiagramStore.getState().updateConnectorConfigBatch(connectorId, {
      batch_size: 100,
      maximum_batching_window_in_seconds: 30,
    });

    const serialized = useDiagramStore.getState().serializeDiagramState();
    resetStore();
    useDiagramStore.getState().loadDiagramState(serialized);

    const restored = useDiagramStore.getState().connectors.get(connectorId)!;
    expect(restored.connectionConfig).toEqual({
      batch_size: 100,
      maximum_batching_window_in_seconds: 30,
    });
  });

  it('sets connectionConfig to undefined when connection_config is missing from serialized state', () => {
    // Simulate loading a diagram saved before connection_config was added
    const diagramState = {
      version: 3 as const,
      projectName: 'test',
      environments: [],
      elements: [],
      canvasObjects: [],
      connectors: [
        { id: 'c1', sourceId: 's1', targetId: 't1', connectionType: 'triggers' },
      ],
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
      globalTerraformConfig: { backend: { type: 'local', config: {} }, provider: { region: 'us-east-1' }, versionConstraints: {} },
      globalRoutingMode: 'straight' as const,
    };

    useDiagramStore.getState().loadDiagramState(diagramState as any);

    const connector = useDiagramStore.getState().connectors.get('c1')!;
    expect(connector.connectionConfig).toBeUndefined();
  });

  it('restores empty connectionConfig as empty object (not undefined)', () => {
    const { sourceId, targetId } = addTwoBlocks();
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    // Set connectionConfig to an empty object
    useDiagramStore.setState((state) => {
      const next = new Map(state.connectors);
      const connector = next.get(connectorId)!;
      next.set(connectorId, { ...connector, connectionConfig: {} });
      return { connectors: next };
    });

    const serialized = useDiagramStore.getState().serializeDiagramState();
    resetStore();
    useDiagramStore.getState().loadDiagramState(serialized);

    const restored = useDiagramStore.getState().connectors.get(connectorId)!;
    expect(restored.connectionConfig).toEqual({});
  });
});

describe('Connection Config Persistence - serializeToArchitectureDescription', () => {
  beforeEach(() => {
    resetStore();
  });

  it('includes connection_config with all configured values in exported connections', () => {
    const sourceId = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'api-gateway',
      name: 'api',
      position: { x: 0, y: 0 },
      config: {},
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });
    const targetId = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'lambda',
      name: 'handler',
      position: { x: 200, y: 0 },
      config: {},
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    useDiagramStore.getState().updateConnectorConfigBatch(connectorId, {
      connection_role: 'route_handler',
      http_method: 'DELETE',
      route_path: '/items/{id}',
    });

    const arch = useDiagramStore.getState().serializeToArchitectureDescription();
    const connection = arch.connections.find((c) => c.source === 'api' && c.target === 'handler')!;

    expect(connection.connection_config).toEqual({
      connection_role: 'route_handler',
      http_method: 'DELETE',
      route_path: '/items/{id}',
    });
  });

  it('omits connection_config when connectionConfig is undefined', () => {
    const sourceId = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'lambda',
      name: 'fn',
      position: { x: 0, y: 0 },
      config: {},
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });
    const targetId = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'sns',
      name: 'topic',
      position: { x: 200, y: 0 },
      config: {},
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });
    useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');

    const arch = useDiagramStore.getState().serializeToArchitectureDescription();
    const connection = arch.connections.find((c) => c.source === 'fn' && c.target === 'topic')!;

    expect(connection.connection_config).toBeUndefined();
  });

  it('omits connection_config when connectionConfig is empty object', () => {
    const sourceId = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'lambda',
      name: 'fn',
      position: { x: 0, y: 0 },
      config: {},
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });
    const targetId = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'sqs',
      name: 'queue',
      position: { x: 200, y: 0 },
      config: {},
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    // Set connectionConfig to empty object
    useDiagramStore.setState((state) => {
      const next = new Map(state.connectors);
      const connector = next.get(connectorId)!;
      next.set(connectorId, { ...connector, connectionConfig: {} });
      return { connectors: next };
    });

    const arch = useDiagramStore.getState().serializeToArchitectureDescription();
    const connection = arch.connections.find((c) => c.source === 'fn' && c.target === 'queue')!;

    // Empty config should be omitted from architecture description export
    expect(connection.connection_config).toBeUndefined();
  });

  it('includes connection_config with access_pattern in exported connections', () => {
    const sourceId = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'lambda',
      name: 'processor',
      position: { x: 0, y: 0 },
      config: {},
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });
    const targetId = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'dynamodb',
      name: 'table',
      position: { x: 200, y: 0 },
      config: {},
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    useDiagramStore.getState().updateConnectorConfig(connectorId, 'access_pattern', 'read');

    const arch = useDiagramStore.getState().serializeToArchitectureDescription();
    const connection = arch.connections.find((c) => c.source === 'processor' && c.target === 'table')!;

    expect(connection.connection_config).toEqual({ access_pattern: 'read' });
  });
});

describe('Connection Config Persistence - Round-trip equivalence', () => {
  beforeEach(() => {
    resetStore();
  });

  it('round-trip preserves connectionConfig with all key types (string, number, boolean)', () => {
    const { sourceId, targetId } = addTwoBlocks();
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    useDiagramStore.getState().updateConnectorConfigBatch(connectorId, {
      connection_role: 'route_handler',
      http_method: 'GET',
      route_path: '/users',
      batch_size: 10,
    });

    const originalConfig = { ...useDiagramStore.getState().connectors.get(connectorId)!.connectionConfig };

    const serialized = useDiagramStore.getState().serializeDiagramState();
    resetStore();
    useDiagramStore.getState().loadDiagramState(serialized);

    const restoredConfig = useDiagramStore.getState().connectors.get(connectorId)!.connectionConfig;
    expect(restoredConfig).toEqual(originalConfig);
  });

  it('round-trip preserves empty connectionConfig as empty object', () => {
    const { sourceId, targetId } = addTwoBlocks();
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    useDiagramStore.setState((state) => {
      const next = new Map(state.connectors);
      const connector = next.get(connectorId)!;
      next.set(connectorId, { ...connector, connectionConfig: {} });
      return { connectors: next };
    });

    const serialized = useDiagramStore.getState().serializeDiagramState();
    resetStore();
    useDiagramStore.getState().loadDiagramState(serialized);

    const restoredConfig = useDiagramStore.getState().connectors.get(connectorId)!.connectionConfig;
    expect(restoredConfig).toEqual({});
  });

  it('round-trip preserves multiple connectors with different configs', () => {
    const apiId = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'api-gateway',
      name: 'api',
      position: { x: 0, y: 0 },
      config: {},
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });
    const lambdaId = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'lambda',
      name: 'fn',
      position: { x: 200, y: 0 },
      config: {},
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });
    const dynamoId = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'dynamodb',
      name: 'table',
      position: { x: 400, y: 0 },
      config: {},
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });

    const conn1 = useDiagramStore.getState().addConnector(apiId, lambdaId, 'triggers');
    useDiagramStore.getState().updateConnectorConfigBatch(conn1, {
      connection_role: 'authorizer',
      authorizer_name: 'my-auth',
      payload_format_version: '2.0',
    });

    const conn2 = useDiagramStore.getState().addConnector(lambdaId, dynamoId, 'triggers');
    useDiagramStore.getState().updateConnectorConfig(conn2, 'access_pattern', 'full');

    const serialized = useDiagramStore.getState().serializeDiagramState();
    resetStore();
    useDiagramStore.getState().loadDiagramState(serialized);

    const restored1 = useDiagramStore.getState().connectors.get(conn1)!;
    expect(restored1.connectionConfig).toEqual({
      connection_role: 'authorizer',
      authorizer_name: 'my-auth',
      payload_format_version: '2.0',
    });

    const restored2 = useDiagramStore.getState().connectors.get(conn2)!;
    expect(restored2.connectionConfig).toEqual({ access_pattern: 'full' });
  });
});
