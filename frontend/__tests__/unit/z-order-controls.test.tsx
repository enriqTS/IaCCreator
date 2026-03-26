import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ZOrderControls from '@/components/config/ZOrderControls';
import { useDiagramStore } from '@/store/diagram-store';
import type { ArchitectureBlock } from '@/types/diagram';
import { DEFAULT_BLOCK_VISUAL } from '@/types/diagram';

function makeBlock(id: string, zIndex: number): ArchitectureBlock {
  return {
    id,
    objectType: 'architecture-block',
    serviceType: 'lambda',
    name: `block-${id}`,
    position: { x: 0, y: 0 },
    config: {},
    visualConfig: { ...DEFAULT_BLOCK_VISUAL },
    zIndex,
  };
}

function setupThreeBlocks() {
  const a = makeBlock('a', 0);
  const b = makeBlock('b', 1);
  const c = makeBlock('c', 2);
  useDiagramStore.setState({
    canvasObjects: new Map([
      ['a', a],
      ['b', b],
      ['c', c],
    ]),
  });
}

describe('ZOrderControls', () => {
  beforeEach(() => {
    useDiagramStore.setState({ canvasObjects: new Map() });
  });

  it('renders all four z-order buttons', () => {
    setupThreeBlocks();
    render(<ZOrderControls objectId="b" />);
    expect(screen.getByTestId('bring-to-front-button')).toBeDefined();
    expect(screen.getByTestId('send-to-back-button')).toBeDefined();
    expect(screen.getByTestId('bring-forward-button')).toBeDefined();
    expect(screen.getByTestId('send-backward-button')).toBeDefined();
  });

  it('Bring to Front sets object zIndex above all others', () => {
    setupThreeBlocks();
    render(<ZOrderControls objectId="a" />);
    fireEvent.click(screen.getByTestId('bring-to-front-button'));
    const obj = useDiagramStore.getState().canvasObjects.get('a')!;
    expect(obj.zIndex).toBeGreaterThan(2);
  });

  it('Send to Back sets object zIndex below all others', () => {
    setupThreeBlocks();
    render(<ZOrderControls objectId="c" />);
    fireEvent.click(screen.getByTestId('send-to-back-button'));
    const obj = useDiagramStore.getState().canvasObjects.get('c')!;
    expect(obj.zIndex).toBeLessThan(0);
  });

  it('Bring Forward swaps zIndex with the object above', () => {
    setupThreeBlocks();
    render(<ZOrderControls objectId="b" />);
    fireEvent.click(screen.getByTestId('bring-forward-button'));
    const b = useDiagramStore.getState().canvasObjects.get('b')!;
    const c = useDiagramStore.getState().canvasObjects.get('c')!;
    expect(b.zIndex).toBe(2);
    expect(c.zIndex).toBe(1);
  });

  it('Send Backward swaps zIndex with the object below', () => {
    setupThreeBlocks();
    render(<ZOrderControls objectId="b" />);
    fireEvent.click(screen.getByTestId('send-backward-button'));
    const a = useDiagramStore.getState().canvasObjects.get('a')!;
    const b = useDiagramStore.getState().canvasObjects.get('b')!;
    expect(b.zIndex).toBe(0);
    expect(a.zIndex).toBe(1);
  });
});
