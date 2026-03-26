import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
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

  it('scales dimensions with viewport scale', () => {
    useDiagramStore.setState({
      viewport: { offsetX: 0, offsetY: 0, scale: 2.0 },
    });
    const block = makeBlock({ visualConfig: { width: 80, height: 80 } });
    render(<ArchitectureBlockComponent block={block} isSelected={false} />);

    const el = screen.getByTestId('architecture-block-block-1');
    expect(el.style.width).toBe('160px');
    expect(el.style.height).toBe('160px');
  });

  it('shows selection highlight border when isSelected is true', () => {
    const block = makeBlock();
    render(<ArchitectureBlockComponent block={block} isSelected={true} />);

    const el = screen.getByTestId('architecture-block-block-1');
    expect(el.style.border).toContain('rgba(59, 130, 246, 0.8)');
  });

  it('shows default border when isSelected is false', () => {
    const block = makeBlock();
    render(<ArchitectureBlockComponent block={block} isSelected={false} />);

    const el = screen.getByTestId('architecture-block-block-1');
    expect(el.style.border).toContain('rgba(255, 255, 255, 0.1)');
  });

  it('centers icon and label within the block', () => {
    const block = makeBlock();
    render(<ArchitectureBlockComponent block={block} isSelected={false} />);

    const el = screen.getByTestId('architecture-block-block-1');
    expect(el.style.display).toBe('flex');
    expect(el.style.alignItems).toBe('center');
    expect(el.style.justifyContent).toBe('center');
  });

  it('positions block using canvas-to-screen transform centered on position', () => {
    useDiagramStore.setState({
      viewport: { offsetX: 10, offsetY: 20, scale: 1.0 },
    });
    const block = makeBlock({
      position: { x: 100, y: 200 },
      visualConfig: { width: 80, height: 80 },
    });
    render(<ArchitectureBlockComponent block={block} isSelected={false} />);

    const el = screen.getByTestId('architecture-block-block-1');
    // screenX = 100 * 1 + 10 = 110, centered: 110 - 40 = 70
    // screenY = 200 * 1 + 20 = 220, centered: 220 - 40 = 180
    expect(el.style.transform).toBe('translate(70px, 180px)');
  });
});
