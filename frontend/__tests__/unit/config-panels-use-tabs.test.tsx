import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import ConfigOverlay from '@/components/config/overlay/ConfigOverlay';
import { useDiagramStore } from '@/store/diagram-store';
import {
  clearConnectionSchemaCache,
  fetchConnectionSchemas,
} from '@/connections/schema-store';
import { getSchemas } from '@/store/schema-store';
import { DEFAULT_BLOCK_VISUAL, DEFAULT_LINE_VISUAL } from '@/types/diagram';
import type { ArchitectureBlock, CanvasObject, Connector, LineObject, ServiceType } from '@/types/diagram';

function makeBlock(id: string, serviceType: ServiceType): ArchitectureBlock {
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

function seed(objects: CanvasObject[], connectors: Connector[] = []) {
  useDiagramStore.setState({
    canvasObjects: new Map(objects.map((o) => [o.id, o])),
    connectors: new Map(connectors.map((c) => [c.id, c])),
    selectedObjectIds: new Set(),
    configOverlayTargetId: null,
  });
}

function open(id: string) {
  act(() => {
    useDiagramStore.getState().openConfigOverlay(id);
  });
}

describe('Every configuration panel is laid out as tabs', () => {
  it('gives a service block one tab per schema group', () => {
    seed([makeBlock('fn', 'lambda')]);
    render(<ConfigOverlay />);

    open('fn');

    expect(screen.getByTestId('schema-tab-bar')).toBeDefined();
    // The backend's groups are the tabs, so General is always among them
    expect(screen.getByTestId('schema-tab-general')).toBeDefined();

    const groups = new Set(
      (getSchemas().lambda ?? []).map((entry) => entry.group ?? 'General'),
    );
    const rendered = screen.getByTestId('schema-tab-bar').querySelectorAll('[role="tab"]');
    expect(rendered.length).toBeGreaterThan(1);
    // Every panel ends with Visual, so the strip is the visible groups plus one
    expect(rendered.length).toBeLessThanOrEqual(groups.size + 1);
    expect(screen.getByTestId('schema-tab-visual')).toBeDefined();
  });

  it('shows only the fields of the open group', () => {
    seed([makeBlock('fn', 'lambda')]);
    render(<ConfigOverlay />);

    open('fn');

    const visible = screen.getAllByTestId(/^config-group-/);
    expect(visible).toHaveLength(1);
  });
});

describe('The connection panel is laid out as tabs', () => {
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
              fields: [
                {
                  key: 'access_pattern',
                  label: 'Access',
                  type: 'select',
                  required: false,
                  default: 'full',
                  options: [{ value: 'full', label: 'Full' }],
                },
              ],
            },
          ],
        }),
      }),
    );
    await fetchConnectionSchemas();

    const line: LineObject = {
      id: 'line-1',
      objectType: 'line',
      name: 'line-1',
      start: { x: 0, y: 0 },
      end: { x: 100, y: 100 },
      sourceAnchor: { objectId: 'fn', anchorPosition: 'right' },
      targetAnchor: { objectId: 'table', anchorPosition: 'left' },
      visualConfig: { ...DEFAULT_LINE_VISUAL },
      zIndex: 0,
    };
    seed(
      [makeBlock('fn', 'lambda'), makeBlock('table', 'dynamodb'), line],
      [{ id: 'conn-1', sourceId: 'fn', targetId: 'table', connectionType: 'accesses' }],
    );
  });

  it('separates the settings from what the connection generates', () => {
    render(<ConfigOverlay />);

    open('line-1');

    expect(screen.getByTestId('connection-tab-settings')).toBeDefined();
    expect(screen.getByTestId('connection-tab-generated')).toBeDefined();
    expect(screen.getByTestId('connection-config-panel')).toBeDefined();
  });
});
