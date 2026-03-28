import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import ElementLayer from '@/components/canvas/ElementLayer';
import { useDiagramStore } from '@/store/diagram-store';
import type { ArchitectureBlock, GeometricObject, LineObject } from '@/types/diagram';

function makeBlock(id: string, zIndex: number): ArchitectureBlock {
  return {
    id,
    objectType: 'architecture-block',
    serviceType: 'lambda',
    name: `block-${id}`,
    position: { x: 100, y: 100 },
    config: {},
    visualConfig: { width: 80, height: 80 },
    zIndex,
  };
}

function makeGeo(id: string, zIndex: number): GeometricObject {
  return {
    id,
    objectType: 'geometric',
    name: `geo-${id}`,
    position: { x: 200, y: 200 },
    visualConfig: {
      width: 120, height: 80, fill: false,
      fillColor: '#3b82f6', borderColor: '#ffffff',
      borderWidth: 2, shape: 'rectangle',
    },
    zIndex,
  };
}

function makeLine(id: string, zIndex: number): LineObject {
  return {
    id,
    objectType: 'line',
    name: `line-${id}`,
    start: { x: 0, y: 0 },
    end: { x: 100, y: 100 },
    sourceAnchor: null,
    targetAnchor: null,
    visualConfig: {
      color: '#ffffff', borderWidth: 2,
      strokeStyle: 'solid', startArrow: false, endArrow: false,
    },
    zIndex,
  };
}

describe('ElementLayer', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      elements: new Map(),
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
    });
  });

  it('renders non-line objects sorted by ascending zIndex', () => {
    const b1 = makeBlock('b1', 5);
    const b2 = makeBlock('b2', 1);
    const g1 = makeGeo('g1', 3);

    useDiagramStore.setState({
      canvasObjects: new Map([
        ['b1', b1],
        ['b2', b2],
        ['g1', g1],
      ]),
    });

    render(<ElementLayer />);

    const blockEl1 = screen.getByTestId('architecture-block-b1');
    const blockEl2 = screen.getByTestId('architecture-block-b2');
    const geoEl = screen.getByTestId('geometric-object-g1');

    // All three should be siblings in the same parent container
    const parent = blockEl1.parentElement!;
    const children = Array.from(parent.children);

    const idxB2 = children.indexOf(blockEl2); // zIndex 1
    const idxG1 = children.indexOf(geoEl);    // zIndex 3
    const idxB1 = children.indexOf(blockEl1); // zIndex 5

    // Ascending zIndex order: b2 (1) < g1 (3) < b1 (5)
    expect(idxB2).toBeLessThan(idxG1);
    expect(idxG1).toBeLessThan(idxB1);
  });

  it('passes isSelected=true for all objects in selectedObjectIds (multi-selection)', () => {
    const b1 = makeBlock('b1', 0);
    const b2 = makeBlock('b2', 1);
    const g1 = makeGeo('g1', 2);

    useDiagramStore.setState({
      canvasObjects: new Map([
        ['b1', b1],
        ['b2', b2],
        ['g1', g1],
      ]),
      selectedObjectIds: new Set(['b1', 'g1']),
    });

    render(<ElementLayer />);

    // b1 and g1 are selected — they should have the selection border
    const blockEl1 = screen.getByTestId('architecture-block-b1');
    expect(blockEl1.style.border).toContain('rgba(59, 130, 246, 0.8)');
    // For geometric objects using SVG path rendering, the selection stroke is on the visible path
    const geoEl = screen.getByTestId('geometric-object-g1');
    const svgPaths = geoEl.querySelectorAll('svg path');
    // The second path is the visible shape — its stroke should be the selection color
    expect(svgPaths.length).toBeGreaterThanOrEqual(2);
    expect(svgPaths[1].getAttribute('stroke')).toBe('rgba(59, 130, 246, 0.8)');

    // b2 is not selected
    const blockEl2 = screen.getByTestId('architecture-block-b2');
    expect(blockEl2.style.border).toContain('transparent');
  });

  it('renders with no objects without errors', () => {
    render(<ElementLayer />);
    // Should not throw; no line SVG overlay rendered
    expect(screen.queryByTestId('line-svg-overlay')).toBeNull();
  });
});
