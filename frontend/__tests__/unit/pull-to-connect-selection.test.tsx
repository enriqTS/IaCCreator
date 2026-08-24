import { describe, it, expect, beforeEach } from 'vitest';
import { render, fireEvent, act } from '@testing-library/react';
import PullToConnectOverlay from '@/components/canvas/interactions/PullToConnectOverlay';
import { useDiagramStore } from '@/store/diagram-store';
import { DEFAULT_BLOCK_VISUAL } from '@/types/diagram';
import type { ArchitectureBlock, CanvasObject, ServiceType } from '@/types/diagram';

function makeBlock(id: string, serviceType: ServiceType, x: number): ArchitectureBlock {
  return {
    id,
    objectType: 'architecture-block',
    serviceType,
    name: id,
    position: { x, y: 0 },
    config: {},
    terraformVariables: {},
    visualConfig: { ...DEFAULT_BLOCK_VISUAL },
    zIndex: 0,
  };
}

function lines(): CanvasObject[] {
  return Array.from(useDiagramStore.getState().canvasObjects.values()).filter(
    (obj) => obj.objectType === 'line',
  );
}

describe('Drawing a connection selects it', () => {
  beforeEach(() => {
    const source = makeBlock('fn', 'lambda', 0);
    const target = makeBlock('table', 'dynamodb', 400);
    useDiagramStore.setState({
      canvasObjects: new Map([
        [source.id, source],
        [target.id, target],
      ]),
      connectors: new Map(),
      selectedObjectIds: new Set(),
      configOverlayTargetId: null,
      viewport: { offsetX: 0, offsetY: 0, scale: 1 },
      pullConnectState: {
        sourceObjectId: 'fn',
        sourceAnchorPoint: { x: 0, y: 0 },
        sourceAnchorPosition: 'right',
      },
    });
  });

  /** Drop on the target block's centre, which is within snapping distance of its anchors. */
  function dropOnTarget() {
    const target = useDiagramStore.getState().canvasObjects.get('table') as ArchitectureBlock;
    const { width } = target.visualConfig;
    act(() => {
      fireEvent.pointerUp(window, {
        clientX: target.position.x + width / 2,
        clientY: target.position.y,
      });
    });
  }

  it('selects the line it just created', () => {
    render(<PullToConnectOverlay />);

    dropOnTarget();

    const created = lines();
    expect(created).toHaveLength(1);
    expect(useDiagramStore.getState().selectedObjectIds).toEqual(new Set([created[0].id]));
  });

  it('opens the configuration for the connection it just drew', () => {
    render(<PullToConnectOverlay />);

    dropOnTarget();

    const created = lines();
    expect(useDiagramStore.getState().configOverlayTargetId).toBe(created[0].id);
  });

  it('leaves the pull-to-connect interaction behind once the line exists', () => {
    render(<PullToConnectOverlay />);

    dropOnTarget();

    expect(useDiagramStore.getState().pullConnectState).toBeNull();
  });

  it('selects a free-floating line drawn away from any block', () => {
    render(<PullToConnectOverlay />);

    act(() => {
      fireEvent.pointerUp(window, { clientX: 900, clientY: 900 });
    });

    const created = lines();
    expect(created).toHaveLength(1);
    expect(useDiagramStore.getState().selectedObjectIds).toEqual(new Set([created[0].id]));
  });
});
