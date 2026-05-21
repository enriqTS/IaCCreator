import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import DragSizingOverlay from '@/components/canvas/DragSizingOverlay';
import { useDiagramStore } from '@/store/diagram-store';
import { useLayoutPreferencesStore } from '@/store/layout-preferences-store';

function makeContainerRef() {
  const div = document.createElement('div');
  div.getBoundingClientRect = () => ({
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
  document.body.appendChild(div);
  return { current: div };
}

describe('DragSizingOverlay', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useDiagramStore.setState({
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
      activeTool: 'pointer',
    });
    // Disable snap-to-grid so tests verify raw drag-sizing behavior
    useLayoutPreferencesStore.setState({ snapToGridEnabled: false });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders nothing when activeTool is pointer', () => {
    const ref = makeContainerRef();
    const onPlace = vi.fn();
    const { container } = render(
      <DragSizingOverlay containerRef={ref} onPlaceObject={onPlace} />,
    );
    expect(container.querySelector('[data-testid="drag-sizing-rect"]')).toBeNull();
  });

  it('renders nothing before mousedown in placement mode', () => {
    useDiagramStore.setState({
      activeTool: { type: 'place-service', serviceType: 'lambda' },
    });
    const ref = makeContainerRef();
    const onPlace = vi.fn();
    const { container } = render(
      <DragSizingOverlay containerRef={ref} onPlaceObject={onPlace} />,
    );
    expect(container.querySelector('[data-testid="drag-sizing-rect"]')).toBeNull();
  });

  it('shows sizing rectangle during drag that exceeds threshold', () => {
    useDiagramStore.setState({
      activeTool: { type: 'place-shape', shape: 'rectangle' },
    });
    const ref = makeContainerRef();
    const onPlace = vi.fn();
    render(<DragSizingOverlay containerRef={ref} onPlaceObject={onPlace} />);

    // mousedown at (100, 100)
    fireEvent.mouseDown(ref.current, { clientX: 100, clientY: 100, button: 0 });
    // Advance past the activation delay
    act(() => { vi.advanceTimersByTime(100); });
    // mousemove to (250, 200) — drag of 150x100, well above threshold
    fireEvent.mouseMove(window, { clientX: 250, clientY: 200 });

    const rect = screen.getByTestId('drag-sizing-rect');
    expect(rect).toBeDefined();
    expect(rect.style.pointerEvents).toBe('none');

    const tooltip = screen.getByTestId('drag-sizing-tooltip');
    expect(tooltip).toBeDefined();
    // Canvas dimensions at scale 1.0: 150 × 100
    expect(tooltip.textContent).toContain('150');
    expect(tooltip.textContent).toContain('100');
  });

  it('does not show rectangle when drag is below threshold', () => {
    useDiagramStore.setState({
      activeTool: { type: 'place-service', serviceType: 'lambda' },
    });
    const ref = makeContainerRef();
    const onPlace = vi.fn();
    const { container } = render(
      <DragSizingOverlay containerRef={ref} onPlaceObject={onPlace} />,
    );

    fireEvent.mouseDown(ref.current, { clientX: 100, clientY: 100, button: 0 });
    // Advance past the activation delay
    act(() => { vi.advanceTimersByTime(100); });
    // Move only 2px — below 5px threshold
    fireEvent.mouseMove(window, { clientX: 102, clientY: 101 });

    expect(container.querySelector('[data-testid="drag-sizing-rect"]')).toBeNull();
  });

  it('calls onPlaceObject with dragged dimensions on mouseup for large drag', () => {
    useDiagramStore.setState({
      activeTool: { type: 'place-shape', shape: 'rectangle' },
    });
    const ref = makeContainerRef();
    const onPlace = vi.fn();
    render(<DragSizingOverlay containerRef={ref} onPlaceObject={onPlace} />);

    fireEvent.mouseDown(ref.current, { clientX: 100, clientY: 100, button: 0 });
    act(() => { vi.advanceTimersByTime(100); });
    fireEvent.mouseMove(window, { clientX: 300, clientY: 250 });
    fireEvent.mouseUp(window, { clientX: 300, clientY: 250, button: 0 });

    expect(onPlace).toHaveBeenCalledTimes(1);
    const payload = onPlace.mock.calls[0][0];
    // Drag of 200x150 in canvas coords at scale 1.0
    expect(payload.width).toBe(200);
    expect(payload.height).toBe(150);
    // Center position
    expect(payload.canvasPosition.x).toBe(200); // 100 + 200/2
    expect(payload.canvasPosition.y).toBe(175); // 100 + 150/2
  });

  it('calls onPlaceObject with zero dimensions for small drag (click)', () => {
    useDiagramStore.setState({
      activeTool: { type: 'place-service', serviceType: 'lambda' },
    });
    const ref = makeContainerRef();
    const onPlace = vi.fn();
    render(<DragSizingOverlay containerRef={ref} onPlaceObject={onPlace} />);

    fireEvent.mouseDown(ref.current, { clientX: 200, clientY: 200, button: 0 });
    fireEvent.mouseMove(window, { clientX: 202, clientY: 201 });
    fireEvent.mouseUp(window, { clientX: 202, clientY: 201, button: 0 });

    expect(onPlace).toHaveBeenCalledTimes(1);
    const payload = onPlace.mock.calls[0][0];
    // Below threshold → width/height = 0 (caller decides defaults)
    expect(payload.width).toBe(0);
    expect(payload.height).toBe(0);
    // Position is the origin canvas point
    expect(payload.canvasPosition.x).toBe(200);
    expect(payload.canvasPosition.y).toBe(200);
  });

  it('enforces minimum 40px dimensions for drag sizing', () => {
    useDiagramStore.setState({
      activeTool: { type: 'place-shape', shape: 'rectangle' },
    });
    const ref = makeContainerRef();
    const onPlace = vi.fn();
    render(<DragSizingOverlay containerRef={ref} onPlaceObject={onPlace} />);

    // Drag 20px wide, 10px tall — above 5px threshold but below 40px minimum
    fireEvent.mouseDown(ref.current, { clientX: 100, clientY: 100, button: 0 });
    act(() => { vi.advanceTimersByTime(100); });
    fireEvent.mouseMove(window, { clientX: 120, clientY: 110 });
    fireEvent.mouseUp(window, { clientX: 120, clientY: 110, button: 0 });

    expect(onPlace).toHaveBeenCalledTimes(1);
    const payload = onPlace.mock.calls[0][0];
    expect(payload.width).toBe(40); // clamped to MIN_OBJECT_WIDTH
    expect(payload.height).toBe(40); // clamped to MIN_OBJECT_HEIGHT
  });

  it('displays dimension tooltip with clamped values', () => {
    useDiagramStore.setState({
      activeTool: { type: 'place-shape', shape: 'rectangle' },
    });
    const ref = makeContainerRef();
    const onPlace = vi.fn();
    render(<DragSizingOverlay containerRef={ref} onPlaceObject={onPlace} />);

    // Drag 15px wide, 8px tall — above threshold, below minimum
    fireEvent.mouseDown(ref.current, { clientX: 100, clientY: 100, button: 0 });
    act(() => { vi.advanceTimersByTime(100); });
    fireEvent.mouseMove(window, { clientX: 115, clientY: 108 });

    const tooltip = screen.getByTestId('drag-sizing-tooltip');
    // Should show clamped values: 40 × 40
    expect(tooltip.textContent).toContain('40');
  });

  it('accounts for viewport scale in canvas dimensions', () => {
    useDiagramStore.setState({
      activeTool: { type: 'place-shape', shape: 'rectangle' },
      viewport: { offsetX: 0, offsetY: 0, scale: 2.0 },
    });
    const ref = makeContainerRef();
    const onPlace = vi.fn();
    render(<DragSizingOverlay containerRef={ref} onPlaceObject={onPlace} />);

    // Drag 200px on screen at scale 2.0 → 100px in canvas coords
    fireEvent.mouseDown(ref.current, { clientX: 100, clientY: 100, button: 0 });
    act(() => { vi.advanceTimersByTime(100); });
    fireEvent.mouseMove(window, { clientX: 300, clientY: 300 });
    fireEvent.mouseUp(window, { clientX: 300, clientY: 300, button: 0 });

    expect(onPlace).toHaveBeenCalledTimes(1);
    const payload = onPlace.mock.calls[0][0];
    expect(payload.width).toBe(100); // 200 screen px / 2.0 scale
    expect(payload.height).toBe(100);
  });

  it('cleans up drag state when tool changes away from placement', () => {
    useDiagramStore.setState({
      activeTool: { type: 'place-shape', shape: 'rectangle' },
    });
    const ref = makeContainerRef();
    const onPlace = vi.fn();
    const { container, rerender } = render(
      <DragSizingOverlay containerRef={ref} onPlaceObject={onPlace} />,
    );

    // Start a drag
    fireEvent.mouseDown(ref.current, { clientX: 100, clientY: 100, button: 0 });
    act(() => { vi.advanceTimersByTime(100); });
    fireEvent.mouseMove(window, { clientX: 250, clientY: 200 });
    expect(screen.getByTestId('drag-sizing-rect')).toBeDefined();

    // Switch tool
    act(() => {
      useDiagramStore.setState({ activeTool: 'pointer' });
    });
    rerender(<DragSizingOverlay containerRef={ref} onPlaceObject={onPlace} />);

    expect(container.querySelector('[data-testid="drag-sizing-rect"]')).toBeNull();
  });

  it('ignores right-click mousedown', () => {
    useDiagramStore.setState({
      activeTool: { type: 'place-shape', shape: 'rectangle' },
    });
    const ref = makeContainerRef();
    const onPlace = vi.fn();
    const { container } = render(
      <DragSizingOverlay containerRef={ref} onPlaceObject={onPlace} />,
    );

    fireEvent.mouseDown(ref.current, { clientX: 100, clientY: 100, button: 2 });
    act(() => { vi.advanceTimersByTime(100); });
    fireEvent.mouseMove(window, { clientX: 250, clientY: 200 });

    expect(container.querySelector('[data-testid="drag-sizing-rect"]')).toBeNull();
  });

  it('treats mouseup before activation delay as a click even with large movement', () => {
    useDiagramStore.setState({
      activeTool: { type: 'place-shape', shape: 'rectangle' },
    });
    const ref = makeContainerRef();
    const onPlace = vi.fn();
    render(<DragSizingOverlay containerRef={ref} onPlaceObject={onPlace} />);

    // mousedown, move far, but release before the 100ms delay
    fireEvent.mouseDown(ref.current, { clientX: 100, clientY: 100, button: 0 });
    act(() => { vi.advanceTimersByTime(50); }); // only 50ms — not yet activated
    fireEvent.mouseMove(window, { clientX: 300, clientY: 300 });
    fireEvent.mouseUp(window, { clientX: 300, clientY: 300, button: 0 });

    expect(onPlace).toHaveBeenCalledTimes(1);
    const payload = onPlace.mock.calls[0][0];
    // Should be treated as a click (width/height = 0), not a drag
    expect(payload.width).toBe(0);
    expect(payload.height).toBe(0);
  });
});
