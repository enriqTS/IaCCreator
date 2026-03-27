/**
 * Preservation Property Tests: Legacy Element/Connector Undo/Redo Unchanged
 *
 * **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
 *
 * Property 2: Preservation — For all legacy element operations (add, move,
 * configure, rename, remove) and connector operations (add, update type, remove),
 * undo/redo round-trips restore exact state. Viewport operations do not affect
 * undo/redo stacks. MAX_HISTORY cap is enforced. New mutation after undo clears
 * redo stack.
 *
 * EXPECTED: These tests PASS on unfixed code, confirming baseline behavior to preserve.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import {
  serviceTypeArbitrary,
  pointArbitrary,
  resourceConfigArbitrary,
} from '../properties/arbitraries';

function resetStore() {
  useDiagramStore.setState({
    elements: new Map(),
    connectors: new Map(),
    canvasObjects: new Map(),
    selectedObjectIds: new Set(),
    objectGroups: new Map(),
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
    viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
  });
}

/** Deep-compare two element Maps by converting values to sorted JSON */
function elementMapsEqual(
  a: Map<string, unknown>,
  b: Map<string, unknown>,
): boolean {
  if (a.size !== b.size) return false;
  for (const [key, val] of a) {
    const other = b.get(key);
    if (other === undefined) return false;
    if (JSON.stringify(val) !== JSON.stringify(other)) return false;
  }
  return true;
}

// ============================================================================
// OBSERVATION TESTS — Verify baseline behavior on UNFIXED code
// ============================================================================

describe('Preservation Observations: Legacy Element/Connector Undo/Redo', () => {
  beforeEach(() => {
    resetStore();
  });

  /**
   * Observe: addElement('lambda', {x:0,y:0}) → undo() → elements.size === 0
   * and canUndo === false and canRedo === true
   *
   * **Validates: Requirements 3.1**
   */
  it('Observe: addElement → undo → empty state, canUndo=false, canRedo=true', () => {
    useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    expect(useDiagramStore.getState().elements.size).toBe(1);

    useDiagramStore.getState().undo();

    expect(useDiagramStore.getState().elements.size).toBe(0);
    expect(useDiagramStore.getState().canUndo).toBe(false);
    expect(useDiagramStore.getState().canRedo).toBe(true);
  });

  /**
   * Observe: addElement → undo() → redo() → element restored with same serviceType and position
   *
   * **Validates: Requirements 3.1**
   */
  it('Observe: addElement → undo → redo → element restored', () => {
    useDiagramStore.getState().addElement('lambda', { x: 42, y: 99 });
    useDiagramStore.getState().undo();
    useDiagramStore.getState().redo();

    const elements = useDiagramStore.getState().elements;
    expect(elements.size).toBe(1);
    const el = Array.from(elements.values())[0];
    expect(el.serviceType).toBe('lambda');
    expect(el.position).toEqual({ x: 42, y: 99 });
  });

  /**
   * Observe: addElement → updateElementPosition → undo() → position restored to original
   *
   * **Validates: Requirements 3.1**
   */
  it('Observe: addElement → updateElementPosition → undo → position restored', () => {
    const id = useDiagramStore.getState().addElement('lambda', { x: 10, y: 20 });
    useDiagramStore.getState().updateElementPosition(id, { x: 500, y: 600 });

    useDiagramStore.getState().undo();

    const el = useDiagramStore.getState().elements.get(id)!;
    expect(el.position).toEqual({ x: 10, y: 20 });
  });

  /**
   * Observe: addConnector → undo() → connector removed, elements remain
   *
   * **Validates: Requirements 3.2**
   */
  it('Observe: addConnector → undo → connector removed, elements remain', () => {
    const id1 = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    const id2 = useDiagramStore.getState().addElement('s3', { x: 100, y: 0 });
    const cid = useDiagramStore.getState().addConnector(id1, id2);

    expect(useDiagramStore.getState().connectors.size).toBe(1);

    useDiagramStore.getState().undo();

    expect(useDiagramStore.getState().connectors.size).toBe(0);
    expect(useDiagramStore.getState().elements.size).toBe(2);
  });

  /**
   * Observe: After 51+ addElement calls, _undoStack.length <= 50 (MAX_HISTORY trimming)
   *
   * **Validates: Requirements 3.5**
   */
  it('Observe: MAX_HISTORY trimming after 51+ mutations', () => {
    for (let i = 0; i < 55; i++) {
      useDiagramStore.getState().addElement('lambda', { x: i, y: 0 });
    }

    expect(useDiagramStore.getState()._undoStack.length).toBeLessThanOrEqual(50);
  });

  /**
   * Observe: addElement → undo() → addElement (new mutation) → canRedo === false
   *
   * **Validates: Requirements 3.6**
   */
  it('Observe: new mutation after undo clears redo stack', () => {
    useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    useDiagramStore.getState().undo();
    expect(useDiagramStore.getState().canRedo).toBe(true);

    useDiagramStore.getState().addElement('s3', { x: 50, y: 50 });
    expect(useDiagramStore.getState().canRedo).toBe(false);
  });

  /**
   * Observe: loadDiagramState(...) → _undoStack.length === 0 and _redoStack.length === 0
   *
   * **Validates: Requirements 3.4**
   */
  it('Observe: loadDiagramState clears undo/redo stacks', () => {
    useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    useDiagramStore.getState().addElement('s3', { x: 10, y: 10 });
    expect(useDiagramStore.getState()._undoStack.length).toBeGreaterThan(0);

    useDiagramStore.getState().loadDiagramState({
      version: 2,
      projectName: 'test',
      environments: [],
      elements: [],
      connectors: [],
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
    });

    expect(useDiagramStore.getState()._undoStack.length).toBe(0);
    expect(useDiagramStore.getState()._redoStack.length).toBe(0);
  });

  /**
   * Observe: pan() and zoom() do not change _undoStack.length
   *
   * **Validates: Requirements 3.3**
   */
  it('Observe: pan and zoom do not affect undo stack', () => {
    // Add an element to have a non-empty undo stack
    useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
    const stackLenBefore = useDiagramStore.getState()._undoStack.length;

    useDiagramStore.getState().pan(100, 200);
    useDiagramStore.getState().zoom(1.5, { x: 0, y: 0 });
    useDiagramStore.getState().pan(-50, 30);

    expect(useDiagramStore.getState()._undoStack.length).toBe(stackLenBefore);
  });
});

// ============================================================================
// PROPERTY-BASED TESTS — Capture preservation behavior
// ============================================================================

describe('Preservation Property: Legacy Element Undo/Redo Round-Trips', () => {
  beforeEach(() => {
    resetStore();
  });

  /**
   * Property: For any legacy element operation (add, move, configure, rename, remove),
   * undo restores the exact previous elements state and redo restores the post-mutation state.
   *
   * **Validates: Requirements 3.1**
   */
  it('Property: element add → undo → redo round-trip preserves exact state', () => {
    fc.assert(
      fc.property(
        serviceTypeArbitrary(),
        pointArbitrary(),
        (serviceType, position) => {
          resetStore();

          // Snapshot before
          const beforeElements = new Map(useDiagramStore.getState().elements);

          // Add element
          const id = useDiagramStore.getState().addElement(serviceType, position);
          const afterAdd = new Map(useDiagramStore.getState().elements);
          expect(afterAdd.size).toBe(beforeElements.size + 1);

          // Undo → should restore before state
          useDiagramStore.getState().undo();
          expect(useDiagramStore.getState().elements.size).toBe(beforeElements.size);

          // Redo → should restore after-add state
          useDiagramStore.getState().redo();
          const afterRedo = useDiagramStore.getState().elements;
          expect(afterRedo.size).toBe(afterAdd.size);
          const el = afterRedo.get(id);
          expect(el).toBeDefined();
          expect(el!.serviceType).toBe(serviceType);
          expect(el!.position.x).toBe(position.x);
          expect(el!.position.y).toBe(position.y);
        },
      ),
      { numRuns: 50 },
    );
  });

  /**
   * Property: For element position update, undo restores original position.
   *
   * **Validates: Requirements 3.1**
   */
  it('Property: element move → undo restores original position', () => {
    fc.assert(
      fc.property(
        serviceTypeArbitrary(),
        pointArbitrary(),
        pointArbitrary(),
        (serviceType, origPos, newPos) => {
          resetStore();

          const id = useDiagramStore.getState().addElement(serviceType, origPos);
          useDiagramStore.getState().updateElementPosition(id, newPos);

          // Undo move → position should be original
          useDiagramStore.getState().undo();
          const el = useDiagramStore.getState().elements.get(id)!;
          expect(el.position.x).toBe(origPos.x);
          expect(el.position.y).toBe(origPos.y);
        },
      ),
      { numRuns: 50 },
    );
  });

  /**
   * Property: For element config update, undo restores original config.
   *
   * **Validates: Requirements 3.1**
   */
  it('Property: element configure → undo restores original config', () => {
    fc.assert(
      fc.property(
        serviceTypeArbitrary(),
        pointArbitrary(),
        (serviceType, position) => {
          resetStore();

          const id = useDiagramStore.getState().addElement(serviceType, position);
          const origConfig = { ...useDiagramStore.getState().elements.get(id)!.config };

          useDiagramStore.getState().updateElementConfig(id, { handler: 'test.handler' });

          // Undo → config should be original
          useDiagramStore.getState().undo();
          const el = useDiagramStore.getState().elements.get(id)!;
          expect(JSON.stringify(el.config)).toBe(JSON.stringify(origConfig));
        },
      ),
      { numRuns: 50 },
    );
  });

  /**
   * Property: For element rename, undo restores original name.
   *
   * **Validates: Requirements 3.1**
   */
  it('Property: element rename → undo restores original name', () => {
    fc.assert(
      fc.property(
        serviceTypeArbitrary(),
        pointArbitrary(),
        fc.string({ minLength: 1, maxLength: 20 }),
        (serviceType, position, newName) => {
          resetStore();

          const id = useDiagramStore.getState().addElement(serviceType, position);
          const origName = useDiagramStore.getState().elements.get(id)!.name;

          useDiagramStore.getState().updateElementName(id, newName);

          // Undo → name should be original
          useDiagramStore.getState().undo();
          const el = useDiagramStore.getState().elements.get(id)!;
          expect(el.name).toBe(origName);
        },
      ),
      { numRuns: 50 },
    );
  });

  /**
   * Property: For element remove, undo restores the element.
   *
   * **Validates: Requirements 3.1**
   */
  it('Property: element remove → undo restores element', () => {
    fc.assert(
      fc.property(
        serviceTypeArbitrary(),
        pointArbitrary(),
        (serviceType, position) => {
          resetStore();

          const id = useDiagramStore.getState().addElement(serviceType, position);
          const elBefore = { ...useDiagramStore.getState().elements.get(id)! };

          useDiagramStore.getState().removeElement(id);
          expect(useDiagramStore.getState().elements.has(id)).toBe(false);

          // Undo → element should be restored
          useDiagramStore.getState().undo();
          const el = useDiagramStore.getState().elements.get(id)!;
          expect(el).toBeDefined();
          expect(el.serviceType).toBe(elBefore.serviceType);
          expect(el.position.x).toBe(elBefore.position.x);
          expect(el.position.y).toBe(elBefore.position.y);
        },
      ),
      { numRuns: 50 },
    );
  });
});

describe('Preservation Property: Connector Undo/Redo Round-Trips', () => {
  beforeEach(() => {
    resetStore();
  });

  /**
   * Property: For connector add, undo removes the connector and redo restores it.
   *
   * **Validates: Requirements 3.2**
   */
  it('Property: addConnector → undo → redo round-trip preserves connector', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('triggers', 'reads_from', 'writes_to', 'invokes'),
        (connectionType) => {
          resetStore();

          const id1 = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
          const id2 = useDiagramStore.getState().addElement('s3', { x: 100, y: 0 });

          const cid = useDiagramStore.getState().addConnector(id1, id2, connectionType);
          expect(useDiagramStore.getState().connectors.size).toBe(1);

          // Undo → connector removed
          useDiagramStore.getState().undo();
          expect(useDiagramStore.getState().connectors.size).toBe(0);
          expect(useDiagramStore.getState().elements.size).toBe(2);

          // Redo → connector restored
          useDiagramStore.getState().redo();
          expect(useDiagramStore.getState().connectors.size).toBe(1);
          const conn = useDiagramStore.getState().connectors.get(cid)!;
          expect(conn.connectionType).toBe(connectionType);
          expect(conn.sourceId).toBe(id1);
          expect(conn.targetId).toBe(id2);
        },
      ),
      { numRuns: 20 },
    );
  });

  /**
   * Property: For connector type update, undo restores original type.
   *
   * **Validates: Requirements 3.2**
   */
  it('Property: updateConnectorType → undo restores original type', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('triggers', 'reads_from', 'writes_to', 'invokes'),
        fc.constantFrom('triggers', 'reads_from', 'writes_to', 'invokes'),
        (origType, newType) => {
          resetStore();

          const id1 = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
          const id2 = useDiagramStore.getState().addElement('s3', { x: 100, y: 0 });
          const cid = useDiagramStore.getState().addConnector(id1, id2, origType);

          useDiagramStore.getState().updateConnectorType(cid, newType);

          // Undo → type should be original
          useDiagramStore.getState().undo();
          const conn = useDiagramStore.getState().connectors.get(cid)!;
          expect(conn.connectionType).toBe(origType);
        },
      ),
      { numRuns: 20 },
    );
  });

  /**
   * Property: For connector remove, undo restores the connector.
   *
   * **Validates: Requirements 3.2**
   */
  it('Property: removeConnector → undo restores connector', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('triggers', 'reads_from', 'writes_to', 'invokes'),
        (connectionType) => {
          resetStore();

          const id1 = useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
          const id2 = useDiagramStore.getState().addElement('s3', { x: 100, y: 0 });
          const cid = useDiagramStore.getState().addConnector(id1, id2, connectionType);

          useDiagramStore.getState().removeConnector(cid);
          expect(useDiagramStore.getState().connectors.size).toBe(0);

          // Undo → connector restored
          useDiagramStore.getState().undo();
          expect(useDiagramStore.getState().connectors.size).toBe(1);
          const conn = useDiagramStore.getState().connectors.get(cid)!;
          expect(conn.connectionType).toBe(connectionType);
        },
      ),
      { numRuns: 20 },
    );
  });
});

describe('Preservation Property: MAX_HISTORY Cap Enforced', () => {
  beforeEach(() => {
    resetStore();
  });

  /**
   * Property: After N > 50 mutations, _undoStack.length <= 50.
   *
   * **Validates: Requirements 3.5**
   */
  it('Property: MAX_HISTORY cap is enforced after N > 50 mutations', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 51, max: 80 }),
        (numMutations) => {
          resetStore();

          for (let i = 0; i < numMutations; i++) {
            useDiagramStore.getState().addElement('lambda', { x: i, y: 0 });
          }

          expect(useDiagramStore.getState()._undoStack.length).toBeLessThanOrEqual(50);
          expect(useDiagramStore.getState()._undoStack.length).toBe(50);
        },
      ),
      { numRuns: 10 },
    );
  });
});

describe('Preservation Property: New Mutation After Undo Clears Redo Stack', () => {
  beforeEach(() => {
    resetStore();
  });

  /**
   * Property: For any sequence of N element additions followed by undo, a new mutation
   * clears the redo stack (canRedo === false).
   *
   * **Validates: Requirements 3.6**
   */
  it('Property: new mutation after undo clears redo stack', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 10 }),
        serviceTypeArbitrary(),
        pointArbitrary(),
        (numAdds, newServiceType, newPos) => {
          resetStore();

          // Add N elements
          for (let i = 0; i < numAdds; i++) {
            useDiagramStore.getState().addElement('lambda', { x: i * 10, y: 0 });
          }

          // Undo once
          useDiagramStore.getState().undo();
          expect(useDiagramStore.getState().canRedo).toBe(true);
          expect(useDiagramStore.getState()._redoStack.length).toBeGreaterThan(0);

          // New mutation → redo stack cleared
          useDiagramStore.getState().addElement(newServiceType, newPos);
          expect(useDiagramStore.getState().canRedo).toBe(false);
          expect(useDiagramStore.getState()._redoStack.length).toBe(0);
        },
      ),
      { numRuns: 30 },
    );
  });
});

describe('Preservation Property: Viewport Operations Do Not Affect Undo/Redo', () => {
  beforeEach(() => {
    resetStore();
  });

  /**
   * Property: For any sequence of pan and zoom operations, the undo and redo stacks
   * remain unchanged.
   *
   * **Validates: Requirements 3.3, 3.4**
   */
  it('Property: viewport operations (pan, zoom) do not affect undo/redo stacks', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.oneof(
            fc.record({
              type: fc.constant('pan' as const),
              dx: fc.double({ min: -1000, max: 1000, noNaN: true, noDefaultInfinity: true }),
              dy: fc.double({ min: -1000, max: 1000, noNaN: true, noDefaultInfinity: true }),
            }),
            fc.record({
              type: fc.constant('zoom' as const),
              factor: fc.double({ min: 0.1, max: 5.0, noNaN: true, noDefaultInfinity: true }),
              cx: fc.double({ min: -500, max: 500, noNaN: true, noDefaultInfinity: true }),
              cy: fc.double({ min: -500, max: 500, noNaN: true, noDefaultInfinity: true }),
            }),
          ),
          { minLength: 1, maxLength: 10 },
        ),
        (viewportOps) => {
          resetStore();

          // Add an element to have a non-empty undo stack
          useDiagramStore.getState().addElement('lambda', { x: 0, y: 0 });
          const undoLenBefore = useDiagramStore.getState()._undoStack.length;
          const redoLenBefore = useDiagramStore.getState()._redoStack.length;

          // Apply viewport operations
          for (const op of viewportOps) {
            if (op.type === 'pan') {
              useDiagramStore.getState().pan(op.dx, op.dy);
            } else {
              useDiagramStore.getState().zoom(op.factor, { x: op.cx, y: op.cy });
            }
          }

          // Stacks should be unchanged
          expect(useDiagramStore.getState()._undoStack.length).toBe(undoLenBefore);
          expect(useDiagramStore.getState()._redoStack.length).toBe(redoLenBefore);
        },
      ),
      { numRuns: 30 },
    );
  });
});
