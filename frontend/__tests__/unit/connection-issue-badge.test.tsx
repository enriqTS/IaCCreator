import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import ConnectionIssueBadge from '@/components/canvas/objects/ConnectionIssueBadge';
import { useDiagramStore } from '@/store/diagram-store';
import { useConnectionPreviewStore } from '@/store/connection-preview-store';
import { DEFAULT_BLOCK_VISUAL, DEFAULT_LINE_VISUAL } from '@/types/diagram';
import type { ArchitectureBlock, CanvasObject, LineObject, ServiceType } from '@/types/diagram';
import type { ConnectionPreview } from '@/types/connection-preview';

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

const line: LineObject = {
  id: 'line-1',
  objectType: 'line',
  name: 'line-1',
  start: { x: 0, y: 0 },
  end: { x: 100, y: 0 },
  sourceAnchor: { objectId: 'gateway', anchorPosition: 'right' },
  targetAnchor: { objectId: 'fn', anchorPosition: 'left' },
  visualConfig: { ...DEFAULT_LINE_VISUAL },
  zIndex: 0,
};

const preview: ConnectionPreview = {
  source: 'gateway',
  target: 'fn',
  source_id: 'gateway',
  target_id: 'fn',
  connection_type: 'route_handler',
  label: 'API Gateway → Lambda (route handler)',
  resources: [],
  iam: [],
  issues: [{ severity: 'warning', message: 'No route on gateway points at fn.' }],
};

function renderBadge() {
  return render(
    <svg>
      <ConnectionIssueBadge line={line} x={50} y={0} />
    </svg>,
  );
}

describe('ConnectionIssueBadge', () => {
  beforeEach(() => {
    const objects: CanvasObject[] = [
      makeBlock('gateway', 'api-gateway'),
      makeBlock('fn', 'lambda'),
      line,
    ];
    useDiagramStore.setState({
      canvasObjects: new Map(objects.map((o) => [o.id, o])),
      connectors: new Map([
        [
          'conn-1',
          {
            id: 'conn-1',
            sourceId: 'gateway',
            targetId: 'fn',
            connectionType: 'route_handler',
          },
        ],
      ]),
    });
    useConnectionPreviewStore.setState({ previews: new Map(), status: 'ready', error: null });
  });

  it('stays invisible while the backend reports no issue', () => {
    renderBadge();
    expect(screen.queryByTestId('connection-issue-badge-line-1')).toBeNull();
  });

  it('marks the line once the backend reports an incomplete connection', () => {
    useConnectionPreviewStore.setState({ previews: new Map([['conn-1', preview]]) });

    renderBadge();

    const badge = screen.getByTestId('connection-issue-badge-line-1');
    expect(badge.querySelector('title')?.textContent).toContain('No route on gateway');
  });

  it('does not mark a line whose connector has no preview', () => {
    useConnectionPreviewStore.setState({
      previews: new Map([['some-other-connector', preview]]),
    });

    renderBadge();

    expect(screen.queryByTestId('connection-issue-badge-line-1')).toBeNull();
  });
});
