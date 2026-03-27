import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import BottomPanel from '@/components/config/BottomPanel';
import { useDiagramStore } from '@/store/diagram-store';
import type { LineObject, GeometricObject, ArchitectureBlock } from '@/types/diagram';
import { DEFAULT_LINE_VISUAL, DEFAULT_GEO_VISUAL, DEFAULT_BLOCK_VISUAL } from '@/types/diagram';

function makeBlock(id = 'block-1'): ArchitectureBlock {
  return {
    id,
    objectType: 'architecture-block',
    serviceType: 'lambda',
    name: 'lambda-1',
    position: { x: 0, y: 0 },
    config: {},
    terraformVariables: { function_name: '', handler: '', runtime: '', memory_size: 128, timeout: 3 },
    visualConfig: { ...DEFAULT_BLOCK_VISUAL },
    zIndex: 0,
  };
}

function makeLine(id = 'line-1'): LineObject {
  return {
    id,
    objectType: 'line',
    name: 'line-1',
    start: { x: 0, y: 0 },
    end: { x: 100, y: 100 },
    visualConfig: { ...DEFAULT_LINE_VISUAL },
    zIndex: 0,
  };
}

function makeGeo(id = 'geo-1'): GeometricObject {
  return {
    id,
    objectType: 'geometric',
    name: 'rect-1',
    position: { x: 0, y: 0 },
    visualConfig: { ...DEFAULT_GEO_VISUAL },
    zIndex: 0,
  };
}

describe('Delete button in BottomPanel', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
      connectors: new Map(),
      bottomPanelExpanded: true,
    });
  });

  it('renders delete button when an object is selected', () => {
    const line = makeLine();
    useDiagramStore.setState({
      canvasObjects: new Map([[line.id, line]]),
      selectedObjectIds: new Set([line.id]),
    });
    render(<BottomPanel />);
    expect(screen.getByTestId('delete-object-button')).toBeDefined();
  });

  it('removes the selected object when delete button is clicked', () => {
    const geo = makeGeo();
    useDiagramStore.setState({
      canvasObjects: new Map([[geo.id, geo]]),
      selectedObjectIds: new Set([geo.id]),
    });
    render(<BottomPanel />);

    fireEvent.click(screen.getByTestId('delete-object-button'));

    const state = useDiagramStore.getState();
    expect(state.canvasObjects.has(geo.id)).toBe(false);
    expect(state.selectedObjectIds.size).toBe(0);
  });

  it('removes architecture block and cascades to connectors', () => {
    const block = makeBlock();
    useDiagramStore.setState({
      canvasObjects: new Map([[block.id, block]]),
      selectedObjectIds: new Set([block.id]),
      connectors: new Map([
        ['conn-1', { id: 'conn-1', sourceId: block.id, targetId: 'other', connectionType: 'triggers' }],
      ]),
    });
    render(<BottomPanel />);

    fireEvent.click(screen.getByTestId('delete-object-button'));

    const state = useDiagramStore.getState();
    expect(state.canvasObjects.has(block.id)).toBe(false);
    expect(state.connectors.has('conn-1')).toBe(false);
    expect(state.selectedObjectIds.size).toBe(0);
  });
});

describe('Delete key handler', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
      connectors: new Map(),
    });
  });

  it('removes selected object on Delete key press', async () => {
    const line = makeLine();
    useDiagramStore.setState({
      canvasObjects: new Map([[line.id, line]]),
      selectedObjectIds: new Set([line.id]),
    });

    // Import and render Canvas to attach the keydown listener
    const { default: Canvas } = await import('@/components/canvas/Canvas');
    render(<Canvas />);

    fireEvent.keyDown(window, { key: 'Delete' });

    const state = useDiagramStore.getState();
    expect(state.canvasObjects.has(line.id)).toBe(false);
    expect(state.selectedObjectIds.size).toBe(0);
  });

  it('removes selected object on Backspace key press', async () => {
    const geo = makeGeo();
    useDiagramStore.setState({
      canvasObjects: new Map([[geo.id, geo]]),
      selectedObjectIds: new Set([geo.id]),
    });

    const { default: Canvas } = await import('@/components/canvas/Canvas');
    render(<Canvas />);

    fireEvent.keyDown(window, { key: 'Backspace' });

    const state = useDiagramStore.getState();
    expect(state.canvasObjects.has(geo.id)).toBe(false);
    expect(state.selectedObjectIds.size).toBe(0);
  });

  it('does not delete when no object is selected', async () => {
    const line = makeLine();
    useDiagramStore.setState({
      canvasObjects: new Map([[line.id, line]]),
      selectedObjectIds: new Set(),
    });

    const { default: Canvas } = await import('@/components/canvas/Canvas');
    render(<Canvas />);

    fireEvent.keyDown(window, { key: 'Delete' });

    const state = useDiagramStore.getState();
    expect(state.canvasObjects.has(line.id)).toBe(true);
  });

  it('does not delete when target is an input element', async () => {
    const line = makeLine();
    useDiagramStore.setState({
      canvasObjects: new Map([[line.id, line]]),
      selectedObjectIds: new Set([line.id]),
    });

    const { default: Canvas } = await import('@/components/canvas/Canvas');
    render(<Canvas />);

    // Create an input and fire keydown on it
    const input = document.createElement('input');
    document.body.appendChild(input);
    fireEvent.keyDown(input, { key: 'Delete' });

    const state = useDiagramStore.getState();
    expect(state.canvasObjects.has(line.id)).toBe(true);
    document.body.removeChild(input);
  });
});
