import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Canvas from '@/components/canvas/Canvas';
import { useDiagramStore } from '@/store/diagram-store';
import { useLayoutPreferencesStore } from '@/store/layout-preferences-store';
import type { LineObject } from '@/types/diagram';

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

function previewEndpoints(testId: string) {
  const line = screen.getByTestId(testId).querySelector('line') as SVGLineElement;
  return {
    x1: Number(line.getAttribute('x1')),
    y1: Number(line.getAttribute('y1')),
    x2: Number(line.getAttribute('x2')),
    y2: Number(line.getAttribute('y2')),
  };
}

function lineObjects(): LineObject[] {
  return [...useDiagramStore.getState().canvasObjects.values()].filter(
    (o): o is LineObject => o.objectType === 'line',
  );
}

// Both drag-placement tools behave the same way apart from their ids and names
const tools = [
  { type: 'place-line' as const, testId: 'line-drag-preview-svg', name: 'Line' },
  { type: 'place-arrow' as const, testId: 'arrow-drag-preview-svg', name: 'Arrow' },
];

describe('Canvas drag placement', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
      activeTool: 'pointer',
    });
    useLayoutPreferencesStore.setState({ snapToGridEnabled: false, gridCellSize: 20 });
  });

  for (const tool of tools) {
    describe(tool.type, () => {
      it('starts a preview at the press point', () => {
        useDiagramStore.setState({ activeTool: { type: tool.type } });
        const container = renderCanvas();

        fireEvent.pointerDown(container, { clientX: 120, clientY: 90, button: 0 });

        expect(previewEndpoints(tool.testId)).toEqual({
          x1: 120,
          y1: 90,
          x2: 120,
          y2: 90,
        });
      });

      it('extends the preview end while the start stays put', () => {
        useDiagramStore.setState({ activeTool: { type: tool.type } });
        const container = renderCanvas();

        fireEvent.pointerDown(container, { clientX: 120, clientY: 90, button: 0 });
        fireEvent.pointerMove(container, { clientX: 300, clientY: 250 });

        expect(previewEndpoints(tool.testId)).toEqual({
          x1: 120,
          y1: 90,
          x2: 300,
          y2: 250,
        });

        fireEvent.pointerMove(container, { clientX: 200, clientY: 400 });

        expect(previewEndpoints(tool.testId)).toEqual({
          x1: 120,
          y1: 90,
          x2: 200,
          y2: 400,
        });
      });

      it('creates the object with the dragged endpoints on release', () => {
        useDiagramStore.setState({ activeTool: { type: tool.type } });
        const container = renderCanvas();

        fireEvent.pointerDown(container, { clientX: 120, clientY: 90, button: 0 });
        fireEvent.pointerMove(container, { clientX: 300, clientY: 250 });
        fireEvent.pointerUp(window, { clientX: 300, clientY: 250, button: 0 });

        const lines = lineObjects();
        expect(lines).toHaveLength(1);
        expect(lines[0].name).toBe(tool.name);
        expect(lines[0].start).toEqual({ x: 120, y: 90 });
        expect(lines[0].end).toEqual({ x: 300, y: 250 });
        expect(useDiagramStore.getState().activeTool).toBe('pointer');
      });

      it('leaves no preview behind when released without moving', () => {
        useDiagramStore.setState({ activeTool: { type: tool.type } });
        const container = renderCanvas();

        fireEvent.pointerDown(container, { clientX: 120, clientY: 90, button: 0 });
        fireEvent.pointerUp(window, { clientX: 120, clientY: 90, button: 0 });

        expect(screen.queryByTestId(tool.testId)).toBeNull();
        expect(lineObjects()).toHaveLength(0);
        // Below the minimum distance the tool stays armed for another attempt
        expect(useDiagramStore.getState().activeTool).toEqual({ type: tool.type });
      });

      it('snaps the start point to the grid when snapping is enabled', () => {
        useLayoutPreferencesStore.setState({ snapToGridEnabled: true, gridCellSize: 20 });
        useDiagramStore.setState({ activeTool: { type: tool.type } });
        const container = renderCanvas();

        fireEvent.pointerDown(container, { clientX: 113, clientY: 87, button: 0 });

        expect(previewEndpoints(tool.testId)).toMatchObject({ x1: 120, y1: 80 });
      });

      it('does not snap the start point when Alt is held', () => {
        useLayoutPreferencesStore.setState({ snapToGridEnabled: true, gridCellSize: 20 });
        useDiagramStore.setState({ activeTool: { type: tool.type } });
        const container = renderCanvas();

        fireEvent.pointerDown(container, {
          clientX: 113,
          clientY: 87,
          button: 0,
          altKey: true,
        });

        expect(previewEndpoints(tool.testId)).toMatchObject({ x1: 113, y1: 87 });
      });

      it('places the preview in screen space under a panned and zoomed viewport', () => {
        useDiagramStore.setState({
          activeTool: { type: tool.type },
          viewport: { offsetX: 40, offsetY: 25, scale: 2.0 },
        });
        const container = renderCanvas();

        fireEvent.pointerDown(container, { clientX: 240, clientY: 225, button: 0 });
        fireEvent.pointerMove(container, { clientX: 440, clientY: 425 });
        fireEvent.pointerUp(window, { clientX: 440, clientY: 425, button: 0 });

        const lines = lineObjects();
        expect(lines).toHaveLength(1);
        // (240 - 40) / 2 = 100, (225 - 25) / 2 = 100
        expect(lines[0].start).toEqual({ x: 100, y: 100 });
        expect(lines[0].end).toEqual({ x: 200, y: 200 });
      });
    });
  }
});
