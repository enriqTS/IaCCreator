import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import VisualTab from '@/components/config/VisualTab';
import type { ArchitectureBlock, LineObject, GeometricObject } from '@/types/diagram';
import { DEFAULT_BLOCK_VISUAL, DEFAULT_LINE_VISUAL, DEFAULT_GEO_VISUAL } from '@/types/diagram';

function makeBlock(): ArchitectureBlock {
  return {
    id: 'block-1',
    objectType: 'architecture-block',
    serviceType: 'lambda',
    name: 'lambda-1',
    position: { x: 0, y: 0 },
    config: {},
    visualConfig: { ...DEFAULT_BLOCK_VISUAL },
  };
}

function makeLine(): LineObject {
  return {
    id: 'line-1',
    objectType: 'line',
    name: 'line-1',
    start: { x: 0, y: 0 },
    end: { x: 100, y: 100 },
    visualConfig: { ...DEFAULT_LINE_VISUAL },
  };
}

function makeGeo(): GeometricObject {
  return {
    id: 'geo-1',
    objectType: 'geometric',
    name: 'rect-1',
    position: { x: 0, y: 0 },
    visualConfig: { ...DEFAULT_GEO_VISUAL },
  };
}

describe('VisualTab', () => {
  it('renders block-visual-config for architecture blocks', () => {
    render(<VisualTab object={makeBlock()} />);
    expect(screen.getByTestId('block-visual-config')).toBeDefined();
    expect(screen.queryByTestId('line-visual-config')).toBeNull();
    expect(screen.queryByTestId('geo-visual-config')).toBeNull();
  });

  it('renders line-visual-config for line objects', () => {
    render(<VisualTab object={makeLine()} />);
    expect(screen.getByTestId('line-visual-config')).toBeDefined();
    expect(screen.queryByTestId('block-visual-config')).toBeNull();
    expect(screen.queryByTestId('geo-visual-config')).toBeNull();
  });

  it('renders geo-visual-config for geometric objects', () => {
    render(<VisualTab object={makeGeo()} />);
    expect(screen.getByTestId('geo-visual-config')).toBeDefined();
    expect(screen.queryByTestId('block-visual-config')).toBeNull();
    expect(screen.queryByTestId('line-visual-config')).toBeNull();
  });
});
