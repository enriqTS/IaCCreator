import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { useDiagramStore } from '@/store/diagram-store';
import type { ArchitectureBlock } from '@/types/diagram';
import type { SchemaField } from '@/connections';
import LinkedSelectFieldRenderer from '@/components/config/schema/LinkedSelectFieldRenderer';

const METHOD_OPTIONS = ['ANY', 'GET', 'POST', 'DELETE'].map((m) => ({ value: m, label: m }));

const ROUTE_FIELD: SchemaField = {
  key: 'route_path',
  label: 'Route',
  type: 'linkedSelect',
  linkedConfigPath: 'routes',
  displayKey: 'path',
  createTemplate: { methods: ['ANY'], path: '', integration_name: '' },
  targetNameKey: 'integration_name',
  targetIdKey: 'integration_id',
  linkedEntryFields: [
    {
      key: 'methods',
      label: 'Methods',
      type: 'multiSelect',
      defaultValue: ['ANY'],
      options: METHOD_OPTIONS,
      exclusiveOptions: ['ANY'],
    },
  ],
};

// Radix's Select scrolls its highlighted item into view, which jsdom does not implement
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}

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

function setup(routes: Record<string, unknown>[]) {
  const store = useDiagramStore.getState();
  const sourceId = store.addCanvasObject({
    objectType: 'architecture-block',
    serviceType: 'api-gateway',
    name: 'my-api',
    position: { x: 0, y: 0 },
    config: { routes },
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
  const connectorId = useDiagramStore
    .getState()
    .addConnector(sourceId, targetId, 'route_handler');

  const objects = useDiagramStore.getState().canvasObjects;
  return {
    sourceId,
    targetId,
    connectorId,
    sourceBlock: objects.get(sourceId) as ArchitectureBlock,
    targetBlock: objects.get(targetId) as ArchitectureBlock,
  };
}

function routesOf(sourceId: string): Record<string, unknown>[] {
  const block = useDiagramStore.getState().canvasObjects.get(sourceId) as ArchitectureBlock;
  return (block.config as Record<string, unknown>).routes as Record<string, unknown>[];
}

describe('route methods editor', () => {
  beforeEach(() => resetStore());

  it('edits the methods of a route already on the connection', () => {
    const ctx = setup([
      { path: '/users', methods: ['ANY'], integration_id: '', integration_name: 'my-lambda' },
    ]);

    render(
      <LinkedSelectFieldRenderer
        field={ROUTE_FIELD}
        value="/users"
        allValues={{}}
        onChange={() => {}}
        sourceBlock={ctx.sourceBlock}
        targetBlock={ctx.targetBlock}
        connectorId={ctx.connectorId}
      />,
    );

    fireEvent.click(screen.getByTestId('entry-option-methods-GET-/users'));
    expect(routesOf(ctx.sourceId)[0].methods).toEqual(['GET']);
  });

  it('keeps ANY exclusive of the other methods', () => {
    const ctx = setup([
      { path: '/users', methods: ['GET', 'POST'], integration_name: 'my-lambda' },
    ]);

    render(
      <LinkedSelectFieldRenderer
        field={ROUTE_FIELD}
        value="/users"
        allValues={{}}
        onChange={() => {}}
        sourceBlock={ctx.sourceBlock}
        targetBlock={ctx.targetBlock}
        connectorId={ctx.connectorId}
      />,
    );

    fireEvent.click(screen.getByTestId('entry-option-methods-ANY-/users'));
    expect(routesOf(ctx.sourceId)[0].methods).toEqual(['ANY']);
  });

  it('creates a route with the methods chosen in the create form', () => {
    const ctx = setup([]);

    render(
      <LinkedSelectFieldRenderer
        field={ROUTE_FIELD}
        value={undefined}
        allValues={{}}
        onChange={() => {}}
        sourceBlock={ctx.sourceBlock}
        targetBlock={ctx.targetBlock}
        connectorId={ctx.connectorId}
      />,
    );

    // Enter create mode, name the route, then pick its methods
    fireEvent.click(screen.getByTestId('field-route_path'));
    fireEvent.click(screen.getByText('Create new...'));
    fireEvent.change(screen.getByTestId('field-route_path-create'), {
      target: { value: '/orders' },
    });
    fireEvent.click(screen.getByTestId('entry-option-methods-POST-create'));
    fireEvent.click(screen.getByLabelText('Confirm'));

    const routes = routesOf(ctx.sourceId);
    expect(routes).toHaveLength(1);
    expect(routes[0].path).toBe('/orders');
    expect(routes[0].methods).toEqual(['POST']);
    expect(routes[0].integration_id).toBe(ctx.targetId);
  });
});
