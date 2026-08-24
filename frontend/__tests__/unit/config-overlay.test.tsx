import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import ConfigOverlay from '@/components/config/overlay/ConfigOverlay';
import { useDiagramStore } from '@/store/diagram-store';
import {
  clearConnectionSchemaCache,
  fetchConnectionSchemas,
} from '@/connections/schema-store';
import { DEFAULT_BLOCK_VISUAL, DEFAULT_GEO_VISUAL, DEFAULT_LINE_VISUAL } from '@/types/diagram';
import type {
  ArchitectureBlock,
  CanvasObject,
  Connector,
  GeometricObject,
  LineObject,
  ServiceType,
} from '@/types/diagram';

function makeBlock(id: string, serviceType: ServiceType = 'lambda'): ArchitectureBlock {
  return {
    id,
    objectType: 'architecture-block',
    serviceType,
    name: id,
    position: { x: 0, y: 0 },
    config: {},
    terraformVariables: {},
    visualConfig: { ...DEFAULT_BLOCK_VISUAL },
    zIndex: 0,
  };
}

function makeGeometric(id: string): GeometricObject {
  return {
    id,
    objectType: 'geometric',
    name: id,
    position: { x: 0, y: 0 },
    visualConfig: { ...DEFAULT_GEO_VISUAL },
    zIndex: 0,
  };
}

function makeLine(id: string, sourceId: string, targetId: string): LineObject {
  return {
    id,
    objectType: 'line',
    name: id,
    start: { x: 0, y: 0 },
    end: { x: 100, y: 100 },
    sourceAnchor: { objectId: sourceId, anchorPosition: 'right' },
    targetAnchor: { objectId: targetId, anchorPosition: 'left' },
    visualConfig: { ...DEFAULT_LINE_VISUAL },
    zIndex: 0,
  };
}

function seed(objects: CanvasObject[], connectors: Connector[] = []) {
  useDiagramStore.setState({
    canvasObjects: new Map(objects.map((o) => [o.id, o])),
    connectors: new Map(connectors.map((c) => [c.id, c])),
    selectedObjectIds: new Set(),
  });
}

function select(id: string | null) {
  act(() => {
    useDiagramStore.getState().selectObject(id);
  });
}

describe('ConfigOverlay', () => {
  beforeEach(() => {
    seed([makeBlock('block-1'), makeBlock('block-2'), makeGeometric('geo-1')]);
  });

  it('stays closed until something configurable is selected', () => {
    render(<ConfigOverlay />);
    expect(screen.queryByTestId('config-overlay')).toBeNull();

    select('block-1');

    expect(screen.getByTestId('config-overlay')).toBeDefined();
    expect(screen.getByTestId('config-overlay-title').textContent).toBe('block-1');
  });

  it('never opens for an object that carries no configuration', () => {
    render(<ConfigOverlay />);
    select('geo-1');
    expect(screen.queryByTestId('config-overlay')).toBeNull();
  });

  it('closes when dismissed and stays closed for the same selection', () => {
    render(<ConfigOverlay />);
    select('block-1');

    fireEvent.click(screen.getByTestId('config-overlay-close'));

    expect(screen.queryByTestId('config-overlay')).toBeNull();
  });

  it('reopens when a different object is selected after a dismissal', () => {
    render(<ConfigOverlay />);
    select('block-1');
    fireEvent.click(screen.getByTestId('config-overlay-close'));

    select('block-2');

    expect(screen.getByTestId('config-overlay')).toBeDefined();
    expect(screen.getByTestId('config-overlay-title').textContent).toBe('block-2');
  });

  it('does not open for a multi-selection', () => {
    render(<ConfigOverlay />);
    act(() => {
      useDiagramStore.setState({ selectedObjectIds: new Set(['block-1', 'block-2']) });
    });
    expect(screen.queryByTestId('config-overlay')).toBeNull();
  });
});

describe('ConfigOverlay for connections', () => {
  beforeEach(async () => {
    clearConnectionSchemaCache();
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          connections: [
            {
              source: 'lambda',
              target: 'dynamodb',
              connection_type: 'accesses',
              label: 'Lambda → DynamoDB',
              is_default: true,
              fields: [],
            },
          ],
        }),
      }),
    );
    await fetchConnectionSchemas();

    const source = makeBlock('fn', 'lambda');
    const target = makeBlock('table', 'dynamodb');
    seed(
      [source, target, makeLine('line-1', 'fn', 'table')],
      [{ id: 'conn-1', sourceId: 'fn', targetId: 'table', connectionType: 'accesses' }],
    );
  });

  it('opens the connection panel from the line, keyed by the connector', () => {
    render(<ConfigOverlay />);
    select('line-1');

    const overlay = screen.getByTestId('config-overlay');
    expect(overlay.getAttribute('data-panel-key')).toBe('conn-1');
    expect(screen.getByTestId('config-overlay-title').textContent).toBe('fn → table');
    expect(screen.getByTestId('connection-overlay-panel')).toBeDefined();
  });

  it('shows what a connection with no fields generates instead of an empty panel', () => {
    render(<ConfigOverlay />);
    select('line-1');

    expect(screen.queryByTestId('connection-config-panel')).toBeNull();
    expect(screen.getByTestId('contribution-preview-empty')).toBeDefined();
  });
});
