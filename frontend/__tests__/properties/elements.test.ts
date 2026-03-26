import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { serviceTypeArbitrary, pointArbitrary } from './arbitraries';

beforeEach(() => {
  useDiagramStore.setState({
    elements: new Map(),
    connectors: new Map(),
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
});

// Feature: diagram-editor-frontend, Property 3: Element creation correctness
// **Validates: Requirements 3.1, 3.5**
describe('Property 3: Element creation correctness', () => {
  test('addElement produces element with correct type, position, unique ID, and default name', () => {
    fc.assert(
      fc.property(
        serviceTypeArbitrary(),
        pointArbitrary(),
        (serviceType, position) => {
          // Reset store before each iteration
          useDiagramStore.setState({
            elements: new Map(),
            connectors: new Map(),
            _undoStack: [],
            _redoStack: [],
            canUndo: false,
            canRedo: false,
          });

          const store = useDiagramStore.getState();
          const id = store.addElement(serviceType, position);

          const element = useDiagramStore.getState().elements.get(id);
          expect(element).toBeDefined();

          // (a) Correct service type
          expect(element!.serviceType).toBe(serviceType);

          // (b) Correct position
          expect(element!.position.x).toBe(position.x);
          expect(element!.position.y).toBe(position.y);

          // (c) Unique ID (non-empty string)
          expect(typeof id).toBe('string');
          expect(id.length).toBeGreaterThan(0);

          // (d) Default name matches {serviceType}-1 (first element of this type)
          expect(element!.name).toBe(`${serviceType}-1`);
        }
      ),
      { numRuns: 100 }
    );
  });

  test('successive elements of the same type get incrementing names', () => {
    fc.assert(
      fc.property(
        serviceTypeArbitrary(),
        pointArbitrary(),
        pointArbitrary(),
        (serviceType, pos1, pos2) => {
          useDiagramStore.setState({
            elements: new Map(),
            connectors: new Map(),
            _undoStack: [],
            _redoStack: [],
            canUndo: false,
            canRedo: false,
          });

          const store = useDiagramStore.getState();
          const id1 = store.addElement(serviceType, pos1);
          const id2 = useDiagramStore.getState().addElement(serviceType, pos2);

          // IDs must be unique
          expect(id1).not.toBe(id2);

          const state = useDiagramStore.getState();
          expect(state.elements.get(id1)!.name).toBe(`${serviceType}-1`);
          expect(state.elements.get(id2)!.name).toBe(`${serviceType}-2`);
        }
      ),
      { numRuns: 100 }
    );
  });
});


// Feature: diagram-editor-frontend, Property 4: Element move preserves connector integrity
// **Validates: Requirements 3.2, 4.3**
describe('Property 4: Element move preserves connector integrity', () => {
  test('moving an element updates only its position; all connectors remain valid', () => {
    fc.assert(
      fc.property(
        serviceTypeArbitrary(),
        serviceTypeArbitrary(),
        pointArbitrary(),
        pointArbitrary(),
        pointArbitrary(),
        (type1, type2, pos1, pos2, newPos) => {
          useDiagramStore.setState({
            elements: new Map(),
            connectors: new Map(),
            _undoStack: [],
            _redoStack: [],
            canUndo: false,
            canRedo: false,
          });

          // Create two elements and a connector between them
          const store = useDiagramStore.getState();
          const id1 = store.addElement(type1, pos1);
          const id2 = useDiagramStore.getState().addElement(type2, pos2);
          const connId = useDiagramStore.getState().addConnector(id1, id2);

          // Snapshot other element and connector before move
          const stateBefore = useDiagramStore.getState();
          const el2Before = { ...stateBefore.elements.get(id2)! };
          const connBefore = { ...stateBefore.connectors.get(connId)! };

          // Move element 1 to new position
          useDiagramStore.getState().updateElementPosition(id1, newPos);

          const stateAfter = useDiagramStore.getState();

          // Moved element has new position
          const movedEl = stateAfter.elements.get(id1)!;
          expect(movedEl.position.x).toBe(newPos.x);
          expect(movedEl.position.y).toBe(newPos.y);

          // Other element is unchanged
          const otherEl = stateAfter.elements.get(id2)!;
          expect(otherEl.position.x).toBe(el2Before.position.x);
          expect(otherEl.position.y).toBe(el2Before.position.y);
          expect(otherEl.serviceType).toBe(el2Before.serviceType);
          expect(otherEl.name).toBe(el2Before.name);

          // Connector still references existing elements
          const conn = stateAfter.connectors.get(connId)!;
          expect(conn).toBeDefined();
          expect(conn.sourceId).toBe(connBefore.sourceId);
          expect(conn.targetId).toBe(connBefore.targetId);
          expect(conn.connectionType).toBe(connBefore.connectionType);
          expect(stateAfter.elements.has(conn.sourceId)).toBe(true);
          expect(stateAfter.elements.has(conn.targetId)).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });
});

// Feature: diagram-editor-frontend, Property 5: Element deletion cascades to connectors
// **Validates: Requirements 3.4**
describe('Property 5: Element deletion cascades to connectors', () => {
  test('deleting an element removes it and all its connectors, nothing else', () => {
    fc.assert(
      fc.property(
        serviceTypeArbitrary(),
        serviceTypeArbitrary(),
        serviceTypeArbitrary(),
        pointArbitrary(),
        pointArbitrary(),
        pointArbitrary(),
        (type1, type2, type3, pos1, pos2, pos3) => {
          useDiagramStore.setState({
            elements: new Map(),
            connectors: new Map(),
            _undoStack: [],
            _redoStack: [],
            canUndo: false,
            canRedo: false,
          });

          // Create three elements
          const store = useDiagramStore.getState();
          const idA = store.addElement(type1, pos1);
          const idB = useDiagramStore.getState().addElement(type2, pos2);
          const idC = useDiagramStore.getState().addElement(type3, pos3);

          // Create connectors: A->B, A->C, B->C
          const connAB = useDiagramStore.getState().addConnector(idA, idB);
          const connAC = useDiagramStore.getState().addConnector(idA, idC);
          const connBC = useDiagramStore.getState().addConnector(idB, idC);

          // Snapshot element B and C, and connector B->C before deletion
          const stateBefore = useDiagramStore.getState();
          const elBBefore = { ...stateBefore.elements.get(idB)! };
          const elCBefore = { ...stateBefore.elements.get(idC)! };
          const connBCBefore = { ...stateBefore.connectors.get(connBC)! };

          // Delete element A
          useDiagramStore.getState().removeElement(idA);

          const stateAfter = useDiagramStore.getState();

          // Element A is removed
          expect(stateAfter.elements.has(idA)).toBe(false);

          // Connectors referencing A are removed
          expect(stateAfter.connectors.has(connAB)).toBe(false);
          expect(stateAfter.connectors.has(connAC)).toBe(false);

          // Element B and C are unchanged
          expect(stateAfter.elements.has(idB)).toBe(true);
          expect(stateAfter.elements.has(idC)).toBe(true);
          const elBAfter = stateAfter.elements.get(idB)!;
          const elCAfter = stateAfter.elements.get(idC)!;
          expect(elBAfter.serviceType).toBe(elBBefore.serviceType);
          expect(elBAfter.name).toBe(elBBefore.name);
          expect(elBAfter.position.x).toBe(elBBefore.position.x);
          expect(elBAfter.position.y).toBe(elBBefore.position.y);
          expect(elCAfter.serviceType).toBe(elCBefore.serviceType);
          expect(elCAfter.name).toBe(elCBefore.name);

          // Connector B->C is preserved
          expect(stateAfter.connectors.has(connBC)).toBe(true);
          const connBCAfter = stateAfter.connectors.get(connBC)!;
          expect(connBCAfter.sourceId).toBe(connBCBefore.sourceId);
          expect(connBCAfter.targetId).toBe(connBCBefore.targetId);

          // No dangling connector references
          for (const [, conn] of stateAfter.connectors) {
            expect(stateAfter.elements.has(conn.sourceId)).toBe(true);
            expect(stateAfter.elements.has(conn.targetId)).toBe(true);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
