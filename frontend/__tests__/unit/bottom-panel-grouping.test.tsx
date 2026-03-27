import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import BottomPanel from '@/components/config/BottomPanel';
import { useDiagramStore } from '@/store/diagram-store';
import type { ArchitectureBlock, GeometricObject } from '@/types/diagram';
import { DEFAULT_BLOCK_VISUAL, DEFAULT_GEO_VISUAL } from '@/types/diagram';

function makeBlock(id: string, groupId?: string): ArchitectureBlock {
  return {
    id,
    objectType: 'architecture-block',
    serviceType: 'lambda',
    name: `block-${id}`,
    position: { x: 0, y: 0 },
    config: {},
    terraformVariables: { function_name: '', handler: '', runtime: '', memory_size: 128, timeout: 3 },
    visualConfig: { ...DEFAULT_BLOCK_VISUAL },
    zIndex: 0,
    ...(groupId !== undefined && { groupId }),
  };
}

function makeGeo(id: string, groupId?: string): GeometricObject {
  return {
    id,
    objectType: 'geometric',
    name: `geo-${id}`,
    position: { x: 0, y: 0 },
    visualConfig: { ...DEFAULT_GEO_VISUAL },
    zIndex: 1,
    ...(groupId !== undefined && { groupId }),
  };
}

describe('BottomPanel group/ungroup controls', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
      objectGroups: new Map(),
      bottomPanelExpanded: true,
    });
  });

  it('shows Group button when 2+ ungrouped objects are selected', () => {
    const b = makeBlock('b1');
    const g = makeGeo('g1');
    useDiagramStore.setState({
      canvasObjects: new Map([[b.id, b], [g.id, g]]),
      selectedObjectIds: new Set([b.id, g.id]),
    });
    render(<BottomPanel />);
    expect(screen.getByTestId('group-button')).toBeDefined();
  });

  it('hides Group button when all selected objects share the same group', () => {
    const groupId = 'grp-1';
    const b = makeBlock('b1', groupId);
    const g = makeGeo('g1', groupId);
    useDiagramStore.setState({
      canvasObjects: new Map([[b.id, b], [g.id, g]]),
      selectedObjectIds: new Set([b.id, g.id]),
      objectGroups: new Map([[groupId, { id: groupId, name: 'Group 1', memberIds: [b.id, g.id] }]]),
    });
    render(<BottomPanel />);
    expect(screen.queryByTestId('group-button')).toBeNull();
  });

  it('shows Ungroup button when any selected object has a groupId', () => {
    const groupId = 'grp-1';
    const b = makeBlock('b1', groupId);
    const g = makeGeo('g1', groupId);
    useDiagramStore.setState({
      canvasObjects: new Map([[b.id, b], [g.id, g]]),
      selectedObjectIds: new Set([b.id, g.id]),
      objectGroups: new Map([[groupId, { id: groupId, name: 'Group 1', memberIds: [b.id, g.id] }]]),
    });
    render(<BottomPanel />);
    expect(screen.getByTestId('ungroup-button')).toBeDefined();
  });

  it('hides Ungroup button when no selected object has a groupId', () => {
    const b = makeBlock('b1');
    const g = makeGeo('g1');
    useDiagramStore.setState({
      canvasObjects: new Map([[b.id, b], [g.id, g]]),
      selectedObjectIds: new Set([b.id, g.id]),
    });
    render(<BottomPanel />);
    expect(screen.queryByTestId('ungroup-button')).toBeNull();
  });

  it('Group button calls groupSelectedObjects', () => {
    const b = makeBlock('b1');
    const g = makeGeo('g1');
    useDiagramStore.setState({
      canvasObjects: new Map([[b.id, b], [g.id, g]]),
      selectedObjectIds: new Set([b.id, g.id]),
    });
    render(<BottomPanel />);
    fireEvent.click(screen.getByTestId('group-button'));

    // After grouping, both objects should have a groupId
    const store = useDiagramStore.getState();
    const obj1 = store.canvasObjects.get('b1');
    const obj2 = store.canvasObjects.get('g1');
    expect(obj1?.groupId).toBeDefined();
    expect(obj2?.groupId).toBeDefined();
    expect(obj1?.groupId).toBe(obj2?.groupId);
    expect(store.objectGroups.size).toBe(1);
  });

  it('Ungroup button calls ungroupObjects for the first found groupId', () => {
    const groupId = 'grp-1';
    const b = makeBlock('b1', groupId);
    const g = makeGeo('g1', groupId);
    useDiagramStore.setState({
      canvasObjects: new Map([[b.id, b], [g.id, g]]),
      selectedObjectIds: new Set([b.id, g.id]),
      objectGroups: new Map([[groupId, { id: groupId, name: 'Group 1', memberIds: [b.id, g.id] }]]),
    });
    render(<BottomPanel />);
    fireEvent.click(screen.getByTestId('ungroup-button'));

    const store = useDiagramStore.getState();
    expect(store.objectGroups.size).toBe(0);
    expect(store.canvasObjects.get('b1')?.groupId).toBeUndefined();
    expect(store.canvasObjects.get('g1')?.groupId).toBeUndefined();
  });

  it('does not show group/ungroup buttons with single selection', () => {
    const b = makeBlock('b1');
    useDiagramStore.setState({
      canvasObjects: new Map([[b.id, b]]),
      selectedObjectIds: new Set([b.id]),
    });
    render(<BottomPanel />);
    expect(screen.queryByTestId('group-button')).toBeNull();
    expect(screen.queryByTestId('ungroup-button')).toBeNull();
  });
});
