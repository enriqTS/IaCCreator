import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import BlockVisualConfig from '@/components/config/BlockVisualConfig';
import type { ArchitectureBlock } from '@/types/diagram';
import { DEFAULT_BLOCK_VISUAL, MIN_OBJECT_WIDTH, MIN_OBJECT_HEIGHT } from '@/types/diagram';
import { useDiagramStore } from '@/store/diagram-store';

function makeBlock(overrides?: Partial<ArchitectureBlock['visualConfig']>): ArchitectureBlock {
  return {
    id: 'block-1',
    objectType: 'architecture-block',
    serviceType: 'lambda',
    name: 'lambda-1',
    position: { x: 0, y: 0 },
    config: {},
    visualConfig: { ...DEFAULT_BLOCK_VISUAL, ...overrides },
  };
}

describe('BlockVisualConfig', () => {
  beforeEach(() => {
    const store = useDiagramStore.getState();
    // Reset store canvas objects
    useDiagramStore.setState({ canvasObjects: new Map() });
  });

  it('renders width and height inputs with current values', () => {
    const block = makeBlock({ width: 120, height: 90 });
    render(<BlockVisualConfig object={block} />);

    const widthInput = screen.getByTestId('block-width') as HTMLInputElement;
    const heightInput = screen.getByTestId('block-height') as HTMLInputElement;

    expect(widthInput.value).toBe('120');
    expect(heightInput.value).toBe('90');
  });

  it('calls updateVisualConfig when width changes to a valid value', () => {
    const block = makeBlock();
    // Add the block to the store so updateVisualConfig can find it
    useDiagramStore.setState({
      canvasObjects: new Map([['block-1', block]]),
    });

    render(<BlockVisualConfig object={block} />);

    const widthInput = screen.getByTestId('block-width') as HTMLInputElement;
    fireEvent.change(widthInput, { target: { value: '150' } });

    const stored = useDiagramStore.getState().canvasObjects.get('block-1') as ArchitectureBlock;
    expect(stored.visualConfig.width).toBe(150);
  });

  it('calls updateVisualConfig when height changes to a valid value', () => {
    const block = makeBlock();
    useDiagramStore.setState({
      canvasObjects: new Map([['block-1', block]]),
    });

    render(<BlockVisualConfig object={block} />);

    const heightInput = screen.getByTestId('block-height') as HTMLInputElement;
    fireEvent.change(heightInput, { target: { value: '200' } });

    const stored = useDiagramStore.getState().canvasObjects.get('block-1') as ArchitectureBlock;
    expect(stored.visualConfig.height).toBe(200);
  });

  it('clamps width to minimum on blur when value is below 40', () => {
    const block = makeBlock();
    useDiagramStore.setState({
      canvasObjects: new Map([['block-1', block]]),
    });

    render(<BlockVisualConfig object={block} />);

    const widthInput = screen.getByTestId('block-width') as HTMLInputElement;
    fireEvent.change(widthInput, { target: { value: '10' } });
    fireEvent.blur(widthInput);

    expect(widthInput.value).toBe(String(MIN_OBJECT_WIDTH));
    const stored = useDiagramStore.getState().canvasObjects.get('block-1') as ArchitectureBlock;
    expect(stored.visualConfig.width).toBe(MIN_OBJECT_WIDTH);
  });

  it('clamps height to minimum on blur when value is below 40', () => {
    const block = makeBlock();
    useDiagramStore.setState({
      canvasObjects: new Map([['block-1', block]]),
    });

    render(<BlockVisualConfig object={block} />);

    const heightInput = screen.getByTestId('block-height') as HTMLInputElement;
    fireEvent.change(heightInput, { target: { value: '5' } });
    fireEvent.blur(heightInput);

    expect(heightInput.value).toBe(String(MIN_OBJECT_HEIGHT));
    const stored = useDiagramStore.getState().canvasObjects.get('block-1') as ArchitectureBlock;
    expect(stored.visualConfig.height).toBe(MIN_OBJECT_HEIGHT);
  });

  it('handles non-numeric input by clamping to minimum on blur', () => {
    const block = makeBlock();
    useDiagramStore.setState({
      canvasObjects: new Map([['block-1', block]]),
    });

    render(<BlockVisualConfig object={block} />);

    const widthInput = screen.getByTestId('block-width') as HTMLInputElement;
    fireEvent.change(widthInput, { target: { value: '' } });
    fireEvent.blur(widthInput);

    expect(widthInput.value).toBe(String(MIN_OBJECT_WIDTH));
  });

  it('has data-testid on root element', () => {
    const block = makeBlock();
    render(<BlockVisualConfig object={block} />);
    expect(screen.getByTestId('block-visual-config')).toBeDefined();
  });
});
