import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import Canvas from '@/components/canvas/Canvas';
import CanvasObjectContextMenu from '@/components/canvas/interactions/CanvasObjectContextMenu';
import { useDiagramStore } from '@/store/diagram-store';
import { DEFAULT_BLOCK_VISUAL, DEFAULT_GEO_VISUAL } from '@/types/diagram';
import type { ArchitectureBlock, CanvasObject, GeometricObject } from '@/types/diagram';

function makeBlock(id: string): ArchitectureBlock {
  return {
    id,
    objectType: 'architecture-block',
    serviceType: 'lambda',
    name: id,
    position: { x: 100, y: 100 },
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
    position: { x: 300, y: 300 },
    visualConfig: { ...DEFAULT_GEO_VISUAL },
    zIndex: 0,
  };
}

function renderCanvas() {
  render(<Canvas />);
  const container = screen.getByTestId('viewport-transform-container')
    .parentElement as HTMLDivElement;
  container.getBoundingClientRect = () => ({
    left: 0,
    top: 0,
    right: 800,
    bottom: 600,
    width: 800,
    height: 600,
    x: 0,
    y: 0,
    toJSON: () => {},
  });
  return container;
}

function seed(objects: CanvasObject[] = []) {
  useDiagramStore.setState({
    canvasObjects: new Map(objects.map((o) => [o.id, o])),
    connectors: new Map(),
    selectedObjectIds: new Set(),
    configOverlayTargetId: null,
    activeTool: 'pointer',
    viewport: { offsetX: 0, offsetY: 0, scale: 1 },
  });
}

function overlayTarget(): string | null {
  return useDiagramStore.getState().configOverlayTargetId;
}

describe('Placing an object opens its configuration', () => {
  beforeEach(() => seed());

  it('opens the overlay for a service block the moment it is placed', () => {
    useDiagramStore.setState({
      activeTool: { type: 'place-service', serviceType: 'lambda' },
    });
    const container = renderCanvas();

    act(() => {
      fireEvent.mouseDown(container, { clientX: 200, clientY: 200, button: 0 });
      fireEvent.mouseUp(window, { clientX: 200, clientY: 200, button: 0 });
    });

    const placed = [...useDiagramStore.getState().canvasObjects.values()].find(
      (obj) => obj.objectType === 'architecture-block',
    );
    expect(placed).toBeDefined();
    expect(overlayTarget()).toBe(placed!.id);
  });
});

describe('Double-clicking an object opens its configuration', () => {
  beforeEach(() => seed([makeBlock('block-1'), makeGeometric('geo-1')]));

  it('opens the overlay for the object that was double-clicked', () => {
    renderCanvas();

    fireEvent.doubleClick(screen.getByTestId('architecture-block-block-1'));

    expect(overlayTarget()).toBe('block-1');
  });

  it('opens nothing when the double-click lands on empty canvas', () => {
    const container = renderCanvas();

    fireEvent.doubleClick(container, { clientX: 700, clientY: 500 });

    expect(overlayTarget()).toBeNull();
  });

  it('ignores a double-click while a placement tool is active', () => {
    useDiagramStore.setState({
      activeTool: { type: 'place-service', serviceType: 'lambda' },
    });
    renderCanvas();

    fireEvent.doubleClick(screen.getByTestId('architecture-block-block-1'));

    expect(overlayTarget()).toBeNull();
  });
});

describe('The context menu opens configuration', () => {
  beforeEach(() => seed([makeBlock('block-1')]));

  it('opens the overlay from Configure Service', () => {
    act(() => {
      useDiagramStore.getState().selectObject('block-1');
    });
    render(
      <CanvasObjectContextMenu
        menu={{ objectId: 'block-1', x: 0, y: 0 }}
        onClose={() => {}}
      />,
    );

    fireEvent.click(screen.getByText('Configure Service'));

    expect(overlayTarget()).toBe('block-1');
  });
});
