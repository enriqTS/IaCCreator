import { describe, it, expect, beforeEach } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';

function addBlock(name: string, x = 0, y = 0): string {
  return useDiagramStore.getState().addCanvasObject({
    objectType: 'architecture-block',
    serviceType: 'lambda',
    name,
    position: { x, y },
    config: {},
    visualConfig: { width: 80, height: 80 },
  });
}

function getZ(id: string): number {
  return useDiagramStore.getState().canvasObjects.get(id)!.zIndex;
}

function allZIndices(): number[] {
  return Array.from(useDiagramStore.getState().canvasObjects.values()).map((o) => o.zIndex);
}

describe('DiagramStore - Z-Order: addCanvasObject assigns zIndex', () => {
  beforeEach(() => {
    useDiagramStore.setState({ canvasObjects: new Map(), selectedObjectIds: new Set() });
  });

  it('first object gets zIndex 0', () => {
    const id = addBlock('a');
    expect(getZ(id)).toBe(0);
  });

  it('subsequent objects get incrementing zIndex', () => {
    const id1 = addBlock('a');
    const id2 = addBlock('b');
    const id3 = addBlock('c');
    expect(getZ(id1)).toBe(0);
    expect(getZ(id2)).toBe(1);
    expect(getZ(id3)).toBe(2);
  });

  it('new object gets maxZIndex + 1 even after reordering', () => {
    const id1 = addBlock('a');
    const id2 = addBlock('b');
    // bring id1 to front so it has zIndex > id2
    useDiagramStore.getState().bringToFront(id1);
    const id3 = addBlock('c');
    expect(getZ(id3)).toBeGreaterThan(getZ(id1));
    expect(getZ(id3)).toBeGreaterThan(getZ(id2));
  });
});

describe('DiagramStore - Z-Order: bringToFront', () => {
  beforeEach(() => {
    useDiagramStore.setState({ canvasObjects: new Map(), selectedObjectIds: new Set() });
  });

  it('moves object to highest zIndex', () => {
    const id1 = addBlock('a');
    const id2 = addBlock('b');
    const id3 = addBlock('c');

    useDiagramStore.getState().bringToFront(id1);
    expect(getZ(id1)).toBeGreaterThan(getZ(id2));
    expect(getZ(id1)).toBeGreaterThan(getZ(id3));
  });

  it('is no-op if already on top', () => {
    const id1 = addBlock('a');
    const id2 = addBlock('b');
    const zBefore = getZ(id2);
    useDiagramStore.getState().bringToFront(id2);
    expect(getZ(id2)).toBe(zBefore);
  });

  it('is no-op for non-existent id', () => {
    addBlock('a');
    const before = allZIndices();
    useDiagramStore.getState().bringToFront('nonexistent');
    expect(allZIndices()).toEqual(before);
  });

  it('maintains unique zIndex values', () => {
    addBlock('a');
    addBlock('b');
    addBlock('c');
    const id1 = Array.from(useDiagramStore.getState().canvasObjects.keys())[0];
    useDiagramStore.getState().bringToFront(id1);
    const zValues = allZIndices();
    expect(new Set(zValues).size).toBe(zValues.length);
  });
});

describe('DiagramStore - Z-Order: sendToBack', () => {
  beforeEach(() => {
    useDiagramStore.setState({ canvasObjects: new Map(), selectedObjectIds: new Set() });
  });

  it('moves object to lowest zIndex', () => {
    const id1 = addBlock('a');
    const id2 = addBlock('b');
    const id3 = addBlock('c');

    useDiagramStore.getState().sendToBack(id3);
    expect(getZ(id3)).toBeLessThan(getZ(id1));
    expect(getZ(id3)).toBeLessThan(getZ(id2));
  });

  it('is no-op if already at back', () => {
    const id1 = addBlock('a');
    addBlock('b');
    const zBefore = getZ(id1);
    useDiagramStore.getState().sendToBack(id1);
    expect(getZ(id1)).toBe(zBefore);
  });

  it('is no-op for non-existent id', () => {
    addBlock('a');
    const before = allZIndices();
    useDiagramStore.getState().sendToBack('nonexistent');
    expect(allZIndices()).toEqual(before);
  });

  it('maintains unique zIndex values', () => {
    addBlock('a');
    addBlock('b');
    addBlock('c');
    const ids = Array.from(useDiagramStore.getState().canvasObjects.keys());
    useDiagramStore.getState().sendToBack(ids[2]);
    const zValues = allZIndices();
    expect(new Set(zValues).size).toBe(zValues.length);
  });
});

describe('DiagramStore - Z-Order: bringForward', () => {
  beforeEach(() => {
    useDiagramStore.setState({ canvasObjects: new Map(), selectedObjectIds: new Set() });
  });

  it('swaps zIndex with the object directly above', () => {
    const id1 = addBlock('a'); // z=0
    const id2 = addBlock('b'); // z=1
    const id3 = addBlock('c'); // z=2

    useDiagramStore.getState().bringForward(id1);
    // id1 should now have id2's old zIndex, and id2 should have id1's old
    expect(getZ(id1)).toBe(1);
    expect(getZ(id2)).toBe(0);
    expect(getZ(id3)).toBe(2); // unchanged
  });

  it('is no-op if already on top', () => {
    addBlock('a');
    const id2 = addBlock('b');
    const zBefore = getZ(id2);
    useDiagramStore.getState().bringForward(id2);
    expect(getZ(id2)).toBe(zBefore);
  });

  it('is no-op for non-existent id', () => {
    addBlock('a');
    const before = allZIndices();
    useDiagramStore.getState().bringForward('nonexistent');
    expect(allZIndices()).toEqual(before);
  });

  it('maintains unique zIndex values after swap', () => {
    addBlock('a');
    addBlock('b');
    addBlock('c');
    const ids = Array.from(useDiagramStore.getState().canvasObjects.keys());
    useDiagramStore.getState().bringForward(ids[0]);
    const zValues = allZIndices();
    expect(new Set(zValues).size).toBe(zValues.length);
  });
});

describe('DiagramStore - Z-Order: sendBackward', () => {
  beforeEach(() => {
    useDiagramStore.setState({ canvasObjects: new Map(), selectedObjectIds: new Set() });
  });

  it('swaps zIndex with the object directly below', () => {
    const id1 = addBlock('a'); // z=0
    const id2 = addBlock('b'); // z=1
    const id3 = addBlock('c'); // z=2

    useDiagramStore.getState().sendBackward(id3);
    // id3 should now have id2's old zIndex, and id2 should have id3's old
    expect(getZ(id3)).toBe(1);
    expect(getZ(id2)).toBe(2);
    expect(getZ(id1)).toBe(0); // unchanged
  });

  it('is no-op if already at back', () => {
    const id1 = addBlock('a');
    addBlock('b');
    const zBefore = getZ(id1);
    useDiagramStore.getState().sendBackward(id1);
    expect(getZ(id1)).toBe(zBefore);
  });

  it('is no-op for non-existent id', () => {
    addBlock('a');
    const before = allZIndices();
    useDiagramStore.getState().sendBackward('nonexistent');
    expect(allZIndices()).toEqual(before);
  });

  it('maintains unique zIndex values after swap', () => {
    addBlock('a');
    addBlock('b');
    addBlock('c');
    const ids = Array.from(useDiagramStore.getState().canvasObjects.keys());
    useDiagramStore.getState().sendBackward(ids[2]);
    const zValues = allZIndices();
    expect(new Set(zValues).size).toBe(zValues.length);
  });
});

describe('DiagramStore - Z-Order: single object edge cases', () => {
  beforeEach(() => {
    useDiagramStore.setState({ canvasObjects: new Map(), selectedObjectIds: new Set() });
  });

  it('bringToFront is no-op with single object', () => {
    const id = addBlock('a');
    const zBefore = getZ(id);
    useDiagramStore.getState().bringToFront(id);
    expect(getZ(id)).toBe(zBefore);
  });

  it('sendToBack is no-op with single object', () => {
    const id = addBlock('a');
    const zBefore = getZ(id);
    useDiagramStore.getState().sendToBack(id);
    expect(getZ(id)).toBe(zBefore);
  });

  it('bringForward is no-op with single object', () => {
    const id = addBlock('a');
    const zBefore = getZ(id);
    useDiagramStore.getState().bringForward(id);
    expect(getZ(id)).toBe(zBefore);
  });

  it('sendBackward is no-op with single object', () => {
    const id = addBlock('a');
    const zBefore = getZ(id);
    useDiagramStore.getState().sendBackward(id);
    expect(getZ(id)).toBe(zBefore);
  });
});
