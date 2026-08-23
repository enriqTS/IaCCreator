import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Canvas from '@/components/canvas/Canvas';
import { useDiagramStore } from '@/store/diagram-store';
import { DEFAULT_BLOCK_VISUAL } from '@/types/diagram';
import type { CanvasObject, ArchitectureBlock } from '@/types/diagram';

// Blocks are 80×80 and positioned by their centre, so bounds are position ± 40
function makeBlock(id: string, x: number, y: number): ArchitectureBlock {
  return {
    id,
    objectType: 'architecture-block',
    serviceType: 'lambda',
    name: id,
    position: { x, y },
    config: {},
    terraformVariables: {},
    visualConfig: { ...DEFAULT_BLOCK_VISUAL, width: 80, height: 80 },
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

function selectedIds(): string[] {
  return [...useDiagramStore.getState().selectedObjectIds].sort();
}

describe('MarqueeSelection', () => {
  beforeEach(() => {
    const objects: CanvasObject[] = [makeBlock('inside', 100, 100), makeBlock('outside', 500, 400)];
    useDiagramStore.setState({
      canvasObjects: new Map(objects.map((o) => [o.id, o])),
      selectedObjectIds: new Set(),
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
      activeTool: 'pointer',
    });
  });

  it('draws a rectangle while dragging on empty canvas', () => {
    const container = renderCanvas();

    fireEvent.mouseDown(container, { clientX: 20, clientY: 30, button: 0 });
    fireEvent.mouseMove(window, { clientX: 220, clientY: 180 });

    const rect = screen.getByTestId('marquee-selection-rect');
    expect(rect.style.left).toBe('20px');
    expect(rect.style.top).toBe('30px');
    expect(rect.style.width).toBe('200px');
    expect(rect.style.height).toBe('150px');
  });

  it('draws the rectangle from its top-left corner when dragging backwards', () => {
    const container = renderCanvas();

    fireEvent.mouseDown(container, { clientX: 300, clientY: 300, button: 0 });
    fireEvent.mouseMove(window, { clientX: 100, clientY: 200 });

    const rect = screen.getByTestId('marquee-selection-rect');
    expect(rect.style.left).toBe('100px');
    expect(rect.style.top).toBe('200px');
    expect(rect.style.width).toBe('200px');
    expect(rect.style.height).toBe('100px');
  });

  it('highlights the intersected objects during the drag', () => {
    const container = renderCanvas();

    fireEvent.mouseDown(container, { clientX: 20, clientY: 20, button: 0 });
    fireEvent.mouseMove(window, { clientX: 200, clientY: 200 });

    expect(screen.getByTestId('marquee-highlight-inside')).toBeDefined();
    expect(screen.queryByTestId('marquee-highlight-outside')).toBeNull();
  });

  it('selects the intersected objects on release and leaves the rest alone', () => {
    const container = renderCanvas();

    fireEvent.mouseDown(container, { clientX: 20, clientY: 20, button: 0 });
    fireEvent.mouseMove(window, { clientX: 200, clientY: 200 });
    fireEvent.mouseUp(window, { clientX: 200, clientY: 200, button: 0 });

    expect(selectedIds()).toEqual(['inside']);
    expect(screen.queryByTestId('marquee-selection-rect')).toBeNull();
  });

  it('selects both objects when the rectangle spans them', () => {
    const container = renderCanvas();

    fireEvent.mouseDown(container, { clientX: 10, clientY: 10, button: 0 });
    fireEvent.mouseMove(window, { clientX: 600, clientY: 500 });
    fireEvent.mouseUp(window, { clientX: 600, clientY: 500, button: 0 });

    expect(selectedIds()).toEqual(['inside', 'outside']);
  });

  it('accounts for the viewport transform when resolving the rectangle', () => {
    useDiagramStore.setState({ viewport: { offsetX: 300, offsetY: 200, scale: 1.0 } });
    const container = renderCanvas();

    // Screen 320..500 maps to canvas 20..200, which covers the 'inside' block only
    fireEvent.mouseDown(container, { clientX: 320, clientY: 220, button: 0 });
    fireEvent.mouseMove(window, { clientX: 500, clientY: 400 });
    fireEvent.mouseUp(window, { clientX: 500, clientY: 400, button: 0 });

    expect(selectedIds()).toEqual(['inside']);
  });

  it('draws nothing and clears the selection on a click without movement', () => {
    useDiagramStore.setState({ selectedObjectIds: new Set(['inside']) });
    const container = renderCanvas();

    fireEvent.pointerDown(container, { clientX: 400, clientY: 300, button: 0 });
    fireEvent.mouseDown(container, { clientX: 400, clientY: 300, button: 0 });
    expect(screen.queryByTestId('marquee-selection-rect')).toBeNull();

    fireEvent.mouseUp(window, { clientX: 400, clientY: 300, button: 0 });

    expect(screen.queryByTestId('marquee-selection-rect')).toBeNull();
    expect(selectedIds()).toEqual([]);
  });

  it('treats a drag below the movement threshold as a click, not a selection', () => {
    const container = renderCanvas();

    // Press over the 'inside' block and release after 1px of jitter
    fireEvent.mouseDown(container, { clientX: 100, clientY: 100, button: 0 });
    fireEvent.mouseMove(window, { clientX: 101, clientY: 101 });
    fireEvent.mouseUp(window, { clientX: 101, clientY: 101, button: 0 });

    expect(selectedIds()).toEqual([]);
  });

  it('does not start a marquee with a non-pointer tool', () => {
    useDiagramStore.setState({ activeTool: { type: 'place-line' } });
    const container = renderCanvas();

    fireEvent.mouseDown(container, { clientX: 20, clientY: 20, button: 0 });
    fireEvent.mouseMove(window, { clientX: 200, clientY: 200 });

    expect(screen.queryByTestId('marquee-selection-rect')).toBeNull();
  });

  it('ignores a right-button drag', () => {
    const container = renderCanvas();

    fireEvent.mouseDown(container, { clientX: 20, clientY: 20, button: 2 });
    fireEvent.mouseMove(window, { clientX: 200, clientY: 200 });

    expect(screen.queryByTestId('marquee-selection-rect')).toBeNull();
  });
});
