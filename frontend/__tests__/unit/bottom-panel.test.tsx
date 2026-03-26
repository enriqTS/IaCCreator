import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import BottomPanel, { getTabsForObject } from '@/components/config/BottomPanel';
import { useDiagramStore } from '@/store/diagram-store';
import type { ArchitectureBlock, LineObject, GeometricObject } from '@/types/diagram';
import { DEFAULT_BLOCK_VISUAL, DEFAULT_LINE_VISUAL, DEFAULT_GEO_VISUAL } from '@/types/diagram';

function makeBlock(id = 'block-1'): ArchitectureBlock {
  return {
    id,
    objectType: 'architecture-block',
    serviceType: 'lambda',
    name: 'lambda-1',
    position: { x: 0, y: 0 },
    config: {},
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

describe('getTabsForObject', () => {
  it('returns Terraform and Visual tabs for architecture blocks', () => {
    expect(getTabsForObject(makeBlock())).toEqual(['Terraform', 'Visual']);
  });

  it('returns only Visual tab for line objects', () => {
    expect(getTabsForObject(makeLine())).toEqual(['Visual']);
  });

  it('returns only Visual tab for geometric objects', () => {
    expect(getTabsForObject(makeGeo())).toEqual(['Visual']);
  });
});

function selectWithObject(obj: ArchitectureBlock | LineObject | GeometricObject) {
  useDiagramStore.setState({
    canvasObjects: new Map([[obj.id, obj]]),
  });
  useDiagramStore.getState().selectObject(obj.id);
}

describe('BottomPanel', () => {
  beforeEach(() => {
    useDiagramStore.setState({ canvasObjects: new Map() });
    useDiagramStore.getState().selectObject(null);
  });

  it('returns null when no object is selected', () => {
    const { container } = render(<BottomPanel />);
    expect(container.innerHTML).toBe('');
  });

  it('renders panel when an architecture block is selected', () => {
    selectWithObject(makeBlock());
    render(<BottomPanel />);
    expect(screen.getByTestId('bottom-panel')).toBeDefined();
  });

  it('shows Terraform and Visual tabs for architecture block', () => {
    selectWithObject(makeBlock());
    render(<BottomPanel />);
    expect(screen.getByTestId('tab-terraform')).toBeDefined();
    expect(screen.getByTestId('tab-visual')).toBeDefined();
  });

  it('shows only Visual tab for line objects', () => {
    selectWithObject(makeLine());
    render(<BottomPanel />);
    expect(screen.getByTestId('tab-visual')).toBeDefined();
    expect(screen.queryByTestId('tab-terraform')).toBeNull();
  });

  it('shows only Visual tab for geometric objects', () => {
    selectWithObject(makeGeo());
    render(<BottomPanel />);
    expect(screen.getByTestId('tab-visual')).toBeDefined();
    expect(screen.queryByTestId('tab-terraform')).toBeNull();
  });

  it('activates first tab by default for architecture block', () => {
    selectWithObject(makeBlock());
    render(<BottomPanel />);
    expect(screen.getByTestId('terraform-tab-content')).toBeDefined();
  });

  it('activates Visual tab by default for line objects', () => {
    selectWithObject(makeLine());
    render(<BottomPanel />);
    expect(screen.getByTestId('visual-tab-content')).toBeDefined();
  });

  it('switches tab content when clicking a tab', () => {
    selectWithObject(makeBlock());
    render(<BottomPanel />);

    expect(screen.getByTestId('terraform-tab-content')).toBeDefined();

    fireEvent.click(screen.getByTestId('tab-visual'));
    expect(screen.getByTestId('visual-tab-content')).toBeDefined();
    expect(screen.queryByTestId('terraform-tab-content')).toBeNull();

    fireEvent.click(screen.getByTestId('tab-terraform'));
    expect(screen.getByTestId('terraform-tab-content')).toBeDefined();
  });

  it('active tab has highlighted style', () => {
    selectWithObject(makeBlock());
    render(<BottomPanel />);

    const terraformTab = screen.getByTestId('tab-terraform');
    const visualTab = screen.getByTestId('tab-visual');

    expect(terraformTab.style.borderBottomColor).toBe('rgb(59, 130, 246)');
    expect(terraformTab.style.fontWeight).toBe('600');
    expect(visualTab.style.borderBottomColor).toBe('transparent');
  });

  it('closes panel when selection is cleared', () => {
    selectWithObject(makeBlock());
    const { rerender, container } = render(<BottomPanel />);
    expect(screen.getByTestId('bottom-panel')).toBeDefined();

    useDiagramStore.getState().selectObject(null);
    rerender(<BottomPanel />);
    expect(container.innerHTML).toBe('');
  });
});
