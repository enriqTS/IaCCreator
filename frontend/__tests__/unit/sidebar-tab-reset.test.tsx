import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import SidebarPanel from '@/components/config/SidebarPanel';
import { useDiagramStore } from '@/store/diagram-store';
import { DEFAULT_BLOCK_VISUAL, DEFAULT_LINE_VISUAL } from '@/types/diagram';
import type { CanvasObject, ArchitectureBlock, LineObject } from '@/types/diagram';

function makeBlock(id: string): ArchitectureBlock {
  return {
    id,
    objectType: 'architecture-block',
    serviceType: 'lambda',
    name: id,
    position: { x: 0, y: 0 },
    config: {},
    terraformVariables: {},
    visualConfig: { ...DEFAULT_BLOCK_VISUAL },
    zIndex: 0,
  };
}

function makeLine(id: string): LineObject {
  return {
    id,
    objectType: 'line',
    name: id,
    start: { x: 0, y: 0 },
    end: { x: 100, y: 100 },
    sourceAnchor: null,
    targetAnchor: null,
    visualConfig: { ...DEFAULT_LINE_VISUAL },
    zIndex: 0,
  };
}

function select(id: string) {
  act(() => {
    useDiagramStore.getState().selectObject(id);
  });
}

// Radix tab triggers activate on mousedown rather than click
function clickTab(testId: string) {
  fireEvent.mouseDown(screen.getByTestId(testId), { button: 0 });
}

function activeTabName(): string | undefined {
  const bar = screen.getByTestId('tab-bar');
  const selected = bar.querySelector('[data-state="active"]');
  return selected?.textContent ?? undefined;
}

describe('SidebarPanel tab reset', () => {
  beforeEach(() => {
    const objects: CanvasObject[] = [makeBlock('block-1'), makeBlock('block-2'), makeLine('line-1')];
    useDiagramStore.setState({
      canvasObjects: new Map(objects.map((o) => [o.id, o])),
      selectedObjectIds: new Set(),
      connectors: new Map(),
      sidebarExpanded: true,
      sidebarWidth: 320,
    });
  });

  it('returns to the first tab when a different object is selected', () => {
    render(<SidebarPanel />);

    select('block-1');
    clickTab('tab-visual');
    expect(activeTabName()).toBe('Visual');

    select('block-2');

    expect(activeTabName()).toBe('Variables');
    expect(screen.getByTestId('variables-tab-content')).toBeDefined();
  });

  it('falls back to the first available tab when the active tab is not offered', () => {
    render(<SidebarPanel />);

    select('block-1');
    expect(activeTabName()).toBe('Variables');

    // A line offers Connection/Visual, so the Variables tab cannot carry over
    select('line-1');

    expect(activeTabName()).toBe('Connection');
    expect(screen.getByTestId('connection-tab-content')).toBeDefined();
    expect(screen.queryByTestId('variables-tab-content')).toBeNull();
  });

  it('opens on the first tab when it mounts with an object already selected', () => {
    useDiagramStore.setState({ selectedObjectIds: new Set(['block-1']) });

    render(<SidebarPanel />);

    expect(activeTabName()).toBe('Variables');
    expect(screen.getByTestId('variables-tab-content')).toBeDefined();
  });

  it('keeps the chosen tab while the same object stays selected', () => {
    render(<SidebarPanel />);

    select('block-1');
    clickTab('tab-visual');

    act(() => {
      useDiagramStore.getState().updateCanvasObject('block-1', { name: 'renamed' });
    });

    expect(activeTabName()).toBe('Visual');
  });
});
