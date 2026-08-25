import { describe, it, expect, beforeEach } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';
import type { ArchitectureBlock } from '@/types/diagram';

/**
 * Persistence tests for multiSelect and linkedSelect field values.
 *
 */

function resetStore() {
  useDiagramStore.setState({
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

function addApiGatewayAndLambda(apiConfig: Record<string, unknown> = {}) {
  const sourceId = useDiagramStore.getState().addCanvasObject({
    objectType: 'architecture-block',
    serviceType: 'api-gateway',
    name: 'my-api',
    position: { x: 0, y: 0 },
    config: apiConfig,
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

describe('Linked Fields Persistence - multiSelect values', () => {
  beforeEach(() => {
    resetStore();
  });

  it('serializes comma-separated multiSelect http_method correctly', () => {
    const { sourceId, targetId } = addApiGatewayAndLambda();
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    useDiagramStore.getState().updateConnectorConfigBatch(connectorId, {
      connection_role: 'route_handler',
      http_method: 'GET,POST,DELETE',
      route_path: '/users',
    });

    const serialized = useDiagramStore.getState().serializeDiagramState();
    const serializedConnector = serialized.connectors.find((c) => c.id === connectorId)!;

    expect(serializedConnector.connection_config).toEqual({
      connection_role: 'route_handler',
      http_method: 'GET,POST,DELETE',
      route_path: '/users',
    });
  });

  it('restores comma-separated multiSelect http_method correctly after load', () => {
    const { sourceId, targetId } = addApiGatewayAndLambda();
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    useDiagramStore.getState().updateConnectorConfigBatch(connectorId, {
      connection_role: 'route_handler',
      http_method: 'GET,POST,DELETE',
      route_path: '/users',
    });

    const serialized = useDiagramStore.getState().serializeDiagramState();
    resetStore();
    useDiagramStore.getState().loadDiagramState(serialized);

    const restored = useDiagramStore.getState().connectors.get(connectorId)!;
    expect(restored.connectionConfig).toEqual({
      connection_role: 'route_handler',
      http_method: 'GET,POST,DELETE',
      route_path: '/users',
    });
  });

  it('round-trip preserves single-value multiSelect (backward compatible)', () => {
    const { sourceId, targetId } = addApiGatewayAndLambda();
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    useDiagramStore.getState().updateConnectorConfigBatch(connectorId, {
      connection_role: 'route_handler',
      http_method: 'ANY',
      route_path: '/$default',
    });

    const serialized = useDiagramStore.getState().serializeDiagramState();
    resetStore();
    useDiagramStore.getState().loadDiagramState(serialized);

    const restored = useDiagramStore.getState().connectors.get(connectorId)!;
    expect(restored.connectionConfig!.http_method).toBe('ANY');
  });

  it('round-trip preserves all HTTP methods selected as comma-separated string', () => {
    const { sourceId, targetId } = addApiGatewayAndLambda();
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    const allMethods = 'GET,POST,PUT,DELETE,PATCH,OPTIONS,HEAD';
    useDiagramStore.getState().updateConnectorConfigBatch(connectorId, {
      connection_role: 'route_handler',
      http_method: allMethods,
      route_path: '/items',
    });

    const serialized = useDiagramStore.getState().serializeDiagramState();
    resetStore();
    useDiagramStore.getState().loadDiagramState(serialized);

    const restored = useDiagramStore.getState().connectors.get(connectorId)!;
    expect(restored.connectionConfig!.http_method).toBe(allMethods);
  });
});

describe('Linked Fields Persistence - linkedSelect values', () => {
  beforeEach(() => {
    resetStore();
  });

  it('serializes linkedSelect route_path string correctly', () => {
    const { sourceId, targetId } = addApiGatewayAndLambda();
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    useDiagramStore.getState().updateConnectorConfigBatch(connectorId, {
      connection_role: 'route_handler',
      http_method: 'GET',
      route_path: '/users/{id}',
    });

    const serialized = useDiagramStore.getState().serializeDiagramState();
    const serializedConnector = serialized.connectors.find((c) => c.id === connectorId)!;

    expect(serializedConnector.connection_config!.route_path).toBe('/users/{id}');
  });

  it('restores linkedSelect route_path string correctly after load', () => {
    const { sourceId, targetId } = addApiGatewayAndLambda();
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    useDiagramStore.getState().updateConnectorConfigBatch(connectorId, {
      connection_role: 'route_handler',
      http_method: 'POST',
      route_path: '/orders/{orderId}/items',
    });

    const serialized = useDiagramStore.getState().serializeDiagramState();
    resetStore();
    useDiagramStore.getState().loadDiagramState(serialized);

    const restored = useDiagramStore.getState().connectors.get(connectorId)!;
    expect(restored.connectionConfig!.route_path).toBe('/orders/{orderId}/items');
  });

  it('round-trip preserves route_path with special characters', () => {
    const { sourceId, targetId } = addApiGatewayAndLambda();
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    useDiagramStore.getState().updateConnectorConfigBatch(connectorId, {
      connection_role: 'route_handler',
      http_method: 'GET',
      route_path: '/api/v1/users/{userId}/posts/{postId}',
    });

    const serialized = useDiagramStore.getState().serializeDiagramState();
    resetStore();
    useDiagramStore.getState().loadDiagramState(serialized);

    const restored = useDiagramStore.getState().connectors.get(connectorId)!;
    expect(restored.connectionConfig!.route_path).toBe('/api/v1/users/{userId}/posts/{postId}');
  });
});

describe('Linked Fields Persistence - source block config.routes', () => {
  beforeEach(() => {
    resetStore();
  });

  it('serializes source block config.routes alongside connector config', () => {
    const routes = [
      { methods: ['GET'], path: '/users', integration_name: 'my-lambda' },
      { methods: ['POST'], path: '/users', integration_name: 'my-lambda' },
    ];
    const { sourceId, targetId } = addApiGatewayAndLambda({ routes });
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    useDiagramStore.getState().updateConnectorConfigBatch(connectorId, {
      connection_role: 'route_handler',
      http_method: 'GET',
      route_path: '/users',
    });

    const serialized = useDiagramStore.getState().serializeDiagramState();
    const serializedBlock = serialized.canvasObjects!.find(
      (obj) => obj.id === sourceId
    )!;

    // Auto-integration side effect sets integration_type and payload_format_version
    // on routes whose path matches the connector's route_path
    expect(serializedBlock.config!.routes).toEqual([
      { methods: ['GET'], path: '/users', integration_name: 'my-lambda' },
      { methods: ['POST'], path: '/users', integration_name: 'my-lambda' },
    ]);
  });

  it('restores source block config.routes correctly after load', () => {
    const routes = [
      { methods: ['GET', 'POST'], path: '/items/{id}', integration_name: 'my-lambda' },
      { methods: ['ANY'], path: '/products', integration_name: 'products-fn' },
    ];
    const { sourceId, targetId } = addApiGatewayAndLambda({ routes });
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    useDiagramStore.getState().updateConnectorConfigBatch(connectorId, {
      connection_role: 'route_handler',
      http_method: 'GET,POST',
      route_path: '/items/{id}',
    });

    const serialized = useDiagramStore.getState().serializeDiagramState();
    resetStore();
    useDiagramStore.getState().loadDiagramState(serialized);

    const restoredBlock = useDiagramStore.getState().canvasObjects.get(sourceId)!;
    // Routes round-trip exactly as configured; the store no longer rewrites them
    expect((restoredBlock as ArchitectureBlock).config.routes).toEqual([
      { methods: ['GET', 'POST'], path: '/items/{id}', integration_name: 'my-lambda' },
      { methods: ['ANY'], path: '/products', integration_name: 'products-fn' },
    ]);
  });




  it('round-trip: multiSelect + linkedSelect combined config is equivalent', () => {
    const routes = [
      { methods: ['GET', 'POST'], path: '/users/{id}', integration_name: 'my-lambda' },
    ];
    const { sourceId, targetId } = addApiGatewayAndLambda({ routes });
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    useDiagramStore.getState().updateConnectorConfigBatch(connectorId, {
      connection_role: 'route_handler',
      http_method: 'GET,POST',
      route_path: '/users/{id}',
    });

    const originalConfig = { ...useDiagramStore.getState().connectors.get(connectorId)!.connectionConfig };
    const originalRoutes = [...((useDiagramStore.getState().canvasObjects.get(sourceId) as ArchitectureBlock).config.routes ?? [])];

    const serialized = useDiagramStore.getState().serializeDiagramState();
    resetStore();
    useDiagramStore.getState().loadDiagramState(serialized);

    const restoredConfig = useDiagramStore.getState().connectors.get(connectorId)!.connectionConfig;
    const restoredRoutes = (useDiagramStore.getState().canvasObjects.get(sourceId) as ArchitectureBlock).config.routes;

    expect(restoredConfig).toEqual(originalConfig);
    expect(restoredRoutes).toEqual(originalRoutes);
  });

  it('round-trip: exclusive "ANY" multiSelect value persists correctly', () => {
    const { sourceId, targetId } = addApiGatewayAndLambda();
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    useDiagramStore.getState().updateConnectorConfigBatch(connectorId, {
      connection_role: 'route_handler',
      http_method: 'ANY',
      route_path: '/$default',
    });

    const serialized = useDiagramStore.getState().serializeDiagramState();
    resetStore();
    useDiagramStore.getState().loadDiagramState(serialized);

    const restored = useDiagramStore.getState().connectors.get(connectorId)!;
    expect(restored.connectionConfig).toEqual({
      connection_role: 'route_handler',
      http_method: 'ANY',
      route_path: '/$default',
    });
  });

  it('round-trip: empty route_path string persists correctly', () => {
    const { sourceId, targetId } = addApiGatewayAndLambda();
    const connectorId = useDiagramStore.getState().addConnector(sourceId, targetId, 'triggers');
    useDiagramStore.getState().updateConnectorConfigBatch(connectorId, {
      connection_role: 'route_handler',
      http_method: 'GET',
      route_path: '',
    });

    const serialized = useDiagramStore.getState().serializeDiagramState();
    resetStore();
    useDiagramStore.getState().loadDiagramState(serialized);

    const restored = useDiagramStore.getState().connectors.get(connectorId)!;
    expect(restored.connectionConfig!.route_path).toBe('');
  });
});
