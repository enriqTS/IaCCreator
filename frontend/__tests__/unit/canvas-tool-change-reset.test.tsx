import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import Canvas from '@/components/canvas/Canvas';
import { useDiagramStore } from '@/store/diagram-store';
import { useLayoutPreferencesStore } from '@/store/layout-preferences-store';
import type { Tool } from '@/types/diagram';

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

function setTool(tool: Tool) {
  act(() => {
    useDiagramStore.setState({ activeTool: tool });
  });
}

describe('Canvas tool-change resets', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useDiagramStore.setState({
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
      activeTool: 'pointer',
    });
    useLayoutPreferencesStore.setState({ snapToGridEnabled: false, gridCellSize: 20 });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('clears the place-line drag preview when the tool changes mid-drag', () => {
    useDiagramStore.setState({ activeTool: { type: 'place-line' } });
    const container = renderCanvas();

    fireEvent.pointerDown(container, { clientX: 100, clientY: 100, button: 0 });
    fireEvent.pointerMove(container, { clientX: 200, clientY: 200 });
    expect(screen.getByTestId('line-drag-preview-svg')).toBeDefined();

    setTool('pointer');

    expect(screen.queryByTestId('line-drag-preview-svg')).toBeNull();
  });

  it('clears the place-arrow drag preview when the tool changes mid-drag', () => {
    useDiagramStore.setState({ activeTool: { type: 'place-arrow' } });
    const container = renderCanvas();

    fireEvent.pointerDown(container, { clientX: 100, clientY: 100, button: 0 });
    fireEvent.pointerMove(container, { clientX: 200, clientY: 200 });
    expect(screen.getByTestId('arrow-drag-preview-svg')).toBeDefined();

    setTool('pointer');

    expect(screen.queryByTestId('arrow-drag-preview-svg')).toBeNull();
  });

  it('clears the two-click line preview when the tool changes mid-placement', () => {
    useDiagramStore.setState({ activeTool: 'line' });
    const container = renderCanvas();

    fireEvent.pointerDown(container, { clientX: 100, clientY: 100, button: 0 });
    fireEvent.pointerMove(container, { clientX: 250, clientY: 180 });
    expect(screen.getByTestId('line-preview-svg')).toBeDefined();

    setTool('pointer');

    expect(screen.queryByTestId('line-preview-svg')).toBeNull();
  });

  it('clears the marquee rectangle when the tool changes mid-marquee', () => {
    const container = renderCanvas();

    fireEvent.mouseDown(container, { clientX: 100, clientY: 100, button: 0 });
    fireEvent.mouseMove(window, { clientX: 300, clientY: 250 });
    expect(screen.getByTestId('marquee-selection-rect')).toBeDefined();

    setTool({ type: 'place-service', serviceType: 'lambda' });

    expect(screen.queryByTestId('marquee-selection-rect')).toBeNull();
  });

  it('clears the drag sizing rectangle when the tool changes mid-drag', () => {
    useDiagramStore.setState({ activeTool: { type: 'place-shape', shape: 'rectangle' } });
    const container = renderCanvas();

    fireEvent.mouseDown(container, { clientX: 100, clientY: 100, button: 0 });
    act(() => { vi.advanceTimersByTime(100); });
    fireEvent.mouseMove(window, { clientX: 300, clientY: 250 });
    expect(screen.getByTestId('drag-sizing-rect')).toBeDefined();

    setTool('pointer');

    expect(screen.queryByTestId('drag-sizing-rect')).toBeNull();
  });

  it('clears the placement ghost when leaving place-service', () => {
    useDiagramStore.setState({ activeTool: { type: 'place-service', serviceType: 'lambda' } });
    const container = renderCanvas();

    fireEvent.mouseMove(container, { clientX: 200, clientY: 150 });
    expect(screen.getByTestId('placement-preview')).toBeDefined();

    setTool('pointer');

    expect(screen.queryByTestId('placement-preview')).toBeNull();
  });

  describe('returning to a tool after abandoning a gesture', () => {
    it('does not resume an abandoned place-line drag', () => {
      useDiagramStore.setState({ activeTool: { type: 'place-line' } });
      const container = renderCanvas();

      fireEvent.pointerDown(container, { clientX: 100, clientY: 100, button: 0 });
      fireEvent.pointerMove(container, { clientX: 200, clientY: 200 });

      setTool('pointer');
      setTool({ type: 'place-line' });

      // Moving without pressing again must not revive the abandoned drag
      fireEvent.pointerMove(container, { clientX: 400, clientY: 400 });
      expect(screen.queryByTestId('line-drag-preview-svg')).toBeNull();

      // A fresh press starts from the new point, not the abandoned one
      fireEvent.pointerDown(container, { clientX: 300, clientY: 300, button: 0 });
      fireEvent.pointerMove(container, { clientX: 500, clientY: 450 });
      const line = screen
        .getByTestId('line-drag-preview-svg')
        .querySelector('line') as SVGLineElement;
      expect(line.getAttribute('x1')).toBe('300');
      expect(line.getAttribute('y1')).toBe('300');
    });

    it('does not resume an abandoned place-arrow drag', () => {
      useDiagramStore.setState({ activeTool: { type: 'place-arrow' } });
      const container = renderCanvas();

      fireEvent.pointerDown(container, { clientX: 100, clientY: 100, button: 0 });
      fireEvent.pointerMove(container, { clientX: 200, clientY: 200 });

      setTool('pointer');
      setTool({ type: 'place-arrow' });

      fireEvent.pointerMove(container, { clientX: 400, clientY: 400 });
      expect(screen.queryByTestId('arrow-drag-preview-svg')).toBeNull();

      fireEvent.pointerDown(container, { clientX: 300, clientY: 300, button: 0 });
      fireEvent.pointerMove(container, { clientX: 500, clientY: 450 });
      const line = screen
        .getByTestId('arrow-drag-preview-svg')
        .querySelector('line') as SVGLineElement;
      expect(line.getAttribute('x1')).toBe('300');
      expect(line.getAttribute('y1')).toBe('300');
    });

    it('does not create a line from a place-line drag abandoned mid-gesture', () => {
      useDiagramStore.setState({ activeTool: { type: 'place-line' } });
      const container = renderCanvas();

      fireEvent.pointerDown(container, { clientX: 100, clientY: 100, button: 0 });
      fireEvent.pointerMove(container, { clientX: 300, clientY: 300 });

      setTool('pointer');
      fireEvent.pointerUp(window, { clientX: 300, clientY: 300, button: 0 });

      expect(useDiagramStore.getState().canvasObjects.size).toBe(0);
    });

    it('does not resume an abandoned marquee drag', () => {
      const container = renderCanvas();

      fireEvent.mouseDown(container, { clientX: 100, clientY: 100, button: 0 });
      fireEvent.mouseMove(window, { clientX: 300, clientY: 250 });

      setTool({ type: 'place-service', serviceType: 'lambda' });
      setTool('pointer');

      fireEvent.mouseMove(window, { clientX: 500, clientY: 450 });
      expect(screen.queryByTestId('marquee-selection-rect')).toBeNull();
    });

    it('does not show a stale placement ghost when returning to place-service', () => {
      const serviceTool = { type: 'place-service' as const, serviceType: 'lambda' as const };
      useDiagramStore.setState({ activeTool: serviceTool });
      const container = renderCanvas();

      fireEvent.mouseMove(container, { clientX: 200, clientY: 150 });
      expect(screen.getByTestId('placement-preview')).toBeDefined();

      setTool('pointer');
      setTool(serviceTool);

      // The ghost only reappears once the pointer reports a fresh position
      expect(screen.queryByTestId('placement-preview')).toBeNull();

      fireEvent.mouseMove(container, { clientX: 400, clientY: 300 });
      expect(screen.getByTestId('placement-preview')).toBeDefined();
    });

    it('does not resume an abandoned drag-sizing gesture', () => {
      useDiagramStore.setState({ activeTool: { type: 'place-shape', shape: 'rectangle' } });
      const container = renderCanvas();

      fireEvent.mouseDown(container, { clientX: 100, clientY: 100, button: 0 });
      act(() => { vi.advanceTimersByTime(100); });
      fireEvent.mouseMove(window, { clientX: 300, clientY: 250 });

      setTool('pointer');
      setTool({ type: 'place-shape', shape: 'rectangle' });

      fireEvent.mouseMove(window, { clientX: 500, clientY: 450 });
      expect(screen.queryByTestId('drag-sizing-rect')).toBeNull();
      expect(useDiagramStore.getState().canvasObjects.size).toBe(0);
    });
  });
});
