import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { createRef } from 'react';
import PlacementPreview from '@/components/canvas/PlacementPreview';
import { useDiagramStore } from '@/store/diagram-store';

function makeContainerRef() {
  const div = document.createElement('div');
  // Provide a bounding rect for coordinate calculations
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
  const ref = { current: div };
  return ref;
}

describe('PlacementPreview', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
      activeTool: 'pointer',
    });
  });

  it('renders nothing when activeTool is pointer', () => {
    const ref = makeContainerRef();
    const { container } = render(<PlacementPreview containerRef={ref} />);
    expect(container.querySelector('[data-testid="placement-preview"]')).toBeNull();
  });

  it('renders nothing when activeTool is connector', () => {
    useDiagramStore.setState({ activeTool: 'connector' });
    const ref = makeContainerRef();
    const { container } = render(<PlacementPreview containerRef={ref} />);
    expect(container.querySelector('[data-testid="placement-preview"]')).toBeNull();
  });

  it('renders a preview element when activeTool is place-service and mouse moves', () => {
    useDiagramStore.setState({
      activeTool: { type: 'place-service', serviceType: 'lambda' },
    });
    const ref = makeContainerRef();
    render(<PlacementPreview containerRef={ref} />);

    // Simulate mouse move on the container
    fireEvent.mouseMove(ref.current, { clientX: 200, clientY: 150 });

    const preview = screen.getByTestId('placement-preview');
    expect(preview).toBeDefined();
    expect(preview.style.opacity).toBe('0.5');
    expect(preview.style.pointerEvents).toBe('none');
  });

  it('renders nothing when activeTool is place-shape (shapes use DragSizingOverlay)', () => {
    useDiagramStore.setState({
      activeTool: { type: 'place-shape', shape: 'rectangle' },
    });
    const ref = makeContainerRef();
    const { container } = render(<PlacementPreview containerRef={ref} />);

    fireEvent.mouseMove(ref.current, { clientX: 300, clientY: 250 });

    expect(container.querySelector('[data-testid="placement-preview"]')).toBeNull();
  });

  it('renders nothing for ellipse shape (shapes use DragSizingOverlay)', () => {
    useDiagramStore.setState({
      activeTool: { type: 'place-shape', shape: 'ellipse' },
    });
    const ref = makeContainerRef();
    const { container } = render(<PlacementPreview containerRef={ref} />);

    fireEvent.mouseMove(ref.current, { clientX: 300, clientY: 250 });

    expect(container.querySelector('[data-testid="placement-preview"]')).toBeNull();
  });

  it('cancels placement on Escape key press', () => {
    useDiagramStore.setState({
      activeTool: { type: 'place-service', serviceType: 'lambda' },
    });
    const ref = makeContainerRef();
    render(<PlacementPreview containerRef={ref} />);

    fireEvent.keyDown(window, { key: 'Escape' });

    expect(useDiagramStore.getState().activeTool).toBe('pointer');
  });

  it('shows service icon for place-service mode', () => {
    useDiagramStore.setState({
      activeTool: { type: 'place-service', serviceType: 'lambda' },
    });
    const ref = makeContainerRef();
    render(<PlacementPreview containerRef={ref} />);

    fireEvent.mouseMove(ref.current, { clientX: 200, clientY: 150 });

    const preview = screen.getByTestId('placement-preview');
    const img = preview.querySelector('img');
    expect(img).not.toBeNull();
    expect(img!.getAttribute('alt')).toBe('lambda');
  });

  it('hides preview when mouse leaves the container', () => {
    useDiagramStore.setState({
      activeTool: { type: 'place-service', serviceType: 'lambda' },
    });
    const ref = makeContainerRef();
    const { container } = render(<PlacementPreview containerRef={ref} />);

    // Move mouse in
    fireEvent.mouseMove(ref.current, { clientX: 200, clientY: 150 });
    expect(screen.getByTestId('placement-preview')).toBeDefined();

    // Mouse leaves
    fireEvent.mouseLeave(ref.current);
    expect(container.querySelector('[data-testid="placement-preview"]')).toBeNull();
  });

  it('accounts for viewport scale when positioning the preview', () => {
    useDiagramStore.setState({
      activeTool: { type: 'place-service', serviceType: 'lambda' },
      viewport: { offsetX: 0, offsetY: 0, scale: 2.0 },
    });
    const ref = makeContainerRef();
    render(<PlacementPreview containerRef={ref} />);

    fireEvent.mouseMove(ref.current, { clientX: 200, clientY: 100 });

    const preview = screen.getByTestId('placement-preview');
    // At scale 2.0, default block is 80x80, scaled = 160x160
    expect(preview.style.width).toBe('160px');
    expect(preview.style.height).toBe('160px');
  });
});
