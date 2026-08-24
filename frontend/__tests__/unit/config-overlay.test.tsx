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

function open(id: string) {
  act(() => {
    useDiagramStore.getState().openConfigOverlay(id);
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
    act(() => {
      useDiagramStore.getState().closeConfigOverlay();
    });
  });

  it('never opens from selection alone', () => {
    render(<ConfigOverlay />);

    select('block-1');

    expect(screen.queryByTestId('config-overlay')).toBeNull();
  });

  it('opens for the object it was asked to configure', () => {
    render(<ConfigOverlay />);

    open('block-1');

    expect(screen.getByTestId('config-overlay')).toBeDefined();
    expect(screen.getByTestId('config-overlay-title').textContent).toBe('block-1');
  });

  it('opens a visual-only panel for an object with no settings of its own', () => {
    render(<ConfigOverlay />);

    open('geo-1');

    expect(screen.getByTestId('config-overlay')).toBeDefined();
    expect(screen.getByTestId('visual-tab-visual')).toBeDefined();
  });

  it('closes when its close button is used', () => {
    render(<ConfigOverlay />);
    open('block-1');

    fireEvent.click(screen.getByRole('button', { name: 'Close' }));

    expect(screen.queryByTestId('config-overlay')).toBeNull();
    expect(useDiagramStore.getState().configOverlayTargetId).toBeNull();
  });

  it('closes on Escape', () => {
    render(<ConfigOverlay />);
    open('block-1');

    fireEvent.keyDown(document, { key: 'Escape' });

    expect(screen.queryByTestId('config-overlay')).toBeNull();
    expect(useDiagramStore.getState().configOverlayTargetId).toBeNull();
  });

  it('dims the canvas behind it while it is open', () => {
    render(<ConfigOverlay />);
    open('block-1');

    expect(document.querySelector('[data-slot="dialog-overlay"]')).not.toBeNull();
    expect(screen.getByTestId('config-overlay').getAttribute('role')).toBe('dialog');
  });

  it('switches to whatever it is next asked to configure', () => {
    render(<ConfigOverlay />);
    open('block-1');

    open('block-2');

    expect(screen.getByTestId('config-overlay-title').textContent).toBe('block-2');
  });

  it('stays open while the selection moves elsewhere', () => {
    render(<ConfigOverlay />);
    open('block-1');

    select('block-2');

    expect(screen.getByTestId('config-overlay-title').textContent).toBe('block-1');
  });

  it('closes itself when its target is deleted', () => {
    render(<ConfigOverlay />);
    open('block-1');

    act(() => {
      useDiagramStore.getState().removeCanvasObject('block-1');
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
    open('line-1');

    const overlay = screen.getByTestId('config-overlay');
    expect(overlay.getAttribute('data-panel-key')).toBe('conn-1');
    expect(screen.getByTestId('config-overlay-title').textContent).toBe('fn → table');
    expect(screen.getByTestId('connection-overlay-panel')).toBeDefined();
  });

  it('shows what a connection with no fields generates instead of an empty panel', () => {
    render(<ConfigOverlay />);
    open('line-1');

    expect(screen.queryByTestId('connection-config-panel')).toBeNull();
    expect(screen.getByTestId('contribution-preview-empty')).toBeDefined();
  });
});
