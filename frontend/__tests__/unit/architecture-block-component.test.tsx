import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ArchitectureBlockComponent from '@/components/canvas/ArchitectureBlockComponent';
import { useDiagramStore } from '@/store/diagram-store';
import type { ArchitectureBlock } from '@/types/diagram';

function makeBlock(overrides: Partial<ArchitectureBlock> = {}): ArchitectureBlock {
  return {
    id: 'block-1',
    objectType: 'architecture-block',
    serviceType: 'lambda',
    name: 'lambda-1',
    position: { x: 100, y: 200 },
    config: {},
    visualConfig: { width: 80, height: 80 },
    zIndex: 0,
    ...overrides,
  };
}

describe('ArchitectureBlockComponent', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
    });
  });

  it('renders the block with service icon and name label', () => {
    const block = makeBlock();
    render(<ArchitectureBlockComponent block={block} isSelected={false} />);

    const el = screen.getByTestId('architecture-block-block-1');
    expect(el).toBeDefined();

    // Check name label is rendered
    expect(screen.getByText('lambda-1')).toBeDefined();

    // Check icon is rendered
    const img = el.querySelector('img');
    expect(img).not.toBeNull();
    expect(img!.getAttribute('alt')).toBe('lambda');
  });

  it('respects visualConfig width and height for sizing', () => {
    const block = makeBlock({ visualConfig: { width: 120, height: 100 } });
    render(<ArchitectureBlockComponent block={block} isSelected={false} />);

    const el = screen.getByTestId('architecture-block-block-1');
    expect(el.style.width).toBe('120px');
    expect(el.style.height).toBe('100px');
  });

  it('uses raw canvas dimensions regardless of viewport scale (container handles scaling)', () => {
    useDiagramStore.setState({
      viewport: { offsetX: 0, offsetY: 0, scale: 2.0 },
    });
    const block = makeBlock({ visualConfig: { width: 80, height: 80 } });
    render(<ArchitectureBlockComponent block={block} isSelected={false} />);

    const el = screen.getByTestId('architecture-block-block-1');
    // Component uses raw canvas dimensions; the parent viewport transform container applies scale
    expect(el.style.width).toBe('80px');
    expect(el.style.height).toBe('80px');
  });

  it('shows selection highlight border when isSelected is true', () => {
    const block = makeBlock();
    render(<ArchitectureBlockComponent block={block} isSelected={true} />);

    const el = screen.getByTestId('architecture-block-block-1');
    // Selection border is rendered as a child div with absolute positioning
    const borderDiv = el.querySelector('div');
    expect(borderDiv).not.toBeNull();
    expect(borderDiv!.style.border).toContain('rgba(59, 130, 246, 0.8)');
  });

  it('does not show selection border when isSelected is false', () => {
    const block = makeBlock();
    render(<ArchitectureBlockComponent block={block} isSelected={false} />);

    const el = screen.getByTestId('architecture-block-block-1');
    // No selection border child div when not selected
    const borderDiv = el.querySelector('div[style*="border"]');
    expect(borderDiv).toBeNull();
  });

  it('renders label as a sibling below the block container', () => {
    const block = makeBlock();
    render(<ArchitectureBlockComponent block={block} isSelected={false} />);

    const label = screen.getByTestId('service-label-block-1');
    expect(label).toBeDefined();
    expect(label.textContent).toBe('lambda-1');
    expect(label.style.position).toBe('absolute');
    expect(label.style.textAlign).toBe('center');
    expect(label.style.pointerEvents).toBe('none');
  });

  it('positions block using raw canvas coordinates centered on position (viewport handled by container)', () => {
    useDiagramStore.setState({
      viewport: { offsetX: 10, offsetY: 20, scale: 1.0 },
    });
    const block = makeBlock({
      position: { x: 100, y: 200 },
      visualConfig: { width: 80, height: 80 },
    });
    render(<ArchitectureBlockComponent block={block} isSelected={false} />);

    const el = screen.getByTestId('architecture-block-block-1');
    // Canvas coordinates: centered at (100, 200) with 80x80 → top-left at (60, 160)
    // No viewport transform applied per-object; the parent container handles that
    expect(el.style.transform).toBe('translate(60px, 160px)');
  });

  it('dispatches selectObject on click (mousedown + mouseup without drag)', () => {
    const block = makeBlock();
    // Add the block to the store so selectObject can find it
    useDiagramStore.setState({
      canvasObjects: new Map([[block.id, block]]),
      selectedObjectIds: new Set(),
    });

    render(<ArchitectureBlockComponent block={block} isSelected={false} />);
    const el = screen.getByTestId('architecture-block-block-1');

    // Simulate a click: mousedown then mouseup at the same position
    fireEvent.mouseDown(el, { button: 0, clientX: 100, clientY: 100 });
    // mouseup fires on window, but the mousedown handler selects immediately for non-selected blocks
    // Check that the store was updated
    const { selectedObjectIds } = useDiagramStore.getState();
    expect(selectedObjectIds.has(block.id)).toBe(true);
  });

  // Note: The pendingSelectionId retry mechanism was removed when the component
  // was refactored to use the useSnapDrag hook, which handles selection directly.
});
