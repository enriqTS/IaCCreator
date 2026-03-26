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

// Feature: diagram-editor-frontend, Property 6: Connector creation correctness
// **Validates: Requirements 4.2, 4.5**
describe('Property 6: Connector creation correctness', () => {
  test('addConnector produces connector with correct sourceId, targetId, unique ID, and non-empty connectionType', () => {
    fc.assert(
      fc.property(
        serviceTypeArbitrary(),
        serviceTypeArbitrary(),
        pointArbitrary(),
        pointArbitrary(),
        (type1, type2, pos1, pos2) => {
          // Reset store before each iteration
          useDiagramStore.setState({
            elements: new Map(),
            connectors: new Map(),
            _undoStack: [],
            _redoStack: [],
            canUndo: false,
            canRedo: false,
          });

          // Create two elements
          const store = useDiagramStore.getState();
          const id1 = store.addElement(type1, pos1);
          const id2 = useDiagramStore.getState().addElement(type2, pos2);

          // Snapshot elements before adding connector
          const elsBefore = useDiagramStore.getState().elements;
          const el1Before = { ...elsBefore.get(id1)! };
          const el2Before = { ...elsBefore.get(id2)! };

          // Add connector between them
          const connId = useDiagramStore.getState().addConnector(id1, id2);

          const stateAfter = useDiagramStore.getState();
          const connector = stateAfter.connectors.get(connId);

          // Connector exists
          expect(connector).toBeDefined();

          // Correct sourceId and targetId
          expect(connector!.sourceId).toBe(id1);
          expect(connector!.targetId).toBe(id2);

          // Unique non-empty ID
          expect(typeof connId).toBe('string');
          expect(connId.length).toBeGreaterThan(0);
          expect(connId).not.toBe(id1);
          expect(connId).not.toBe(id2);

          // Non-empty connectionType with "triggers" default
          expect(connector!.connectionType).toBe('triggers');
          expect(connector!.connectionType.length).toBeGreaterThan(0);

          // Connected elements remain unchanged
          const el1After = stateAfter.elements.get(id1)!;
          const el2After = stateAfter.elements.get(id2)!;

          expect(el1After.serviceType).toBe(el1Before.serviceType);
          expect(el1After.name).toBe(el1Before.name);
          expect(el1After.position.x).toBe(el1Before.position.x);
          expect(el1After.position.y).toBe(el1Before.position.y);

          expect(el2After.serviceType).toBe(el2Before.serviceType);
          expect(el2After.name).toBe(el2Before.name);
          expect(el2After.position.x).toBe(el2Before.position.x);
          expect(el2After.position.y).toBe(el2Before.position.y);
        }
      ),
      { numRuns: 100 }
    );
  });
});

// Feature: diagram-editor-frontend, Property 7: Connector deletion preserves elements
// **Validates: Requirements 4.4**
describe('Property 7: Connector deletion preserves elements', () => {
  test('deleting a connector removes only that connector; all elements unchanged', () => {
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

          // Create three elements and two connectors
          const store = useDiagramStore.getState();
          const idA = store.addElement(type1, pos1);
          const idB = useDiagramStore.getState().addElement(type2, pos2);
          const idC = useDiagramStore.getState().addElement(type3, pos3);

          const connAB = useDiagramStore.getState().addConnector(idA, idB);
          const connBC = useDiagramStore.getState().addConnector(idB, idC);

          // Snapshot state before deletion
          const stateBefore = useDiagramStore.getState();
          const elementCountBefore = stateBefore.elements.size;
          const elABefore = { ...stateBefore.elements.get(idA)! };
          const elBBefore = { ...stateBefore.elements.get(idB)! };
          const elCBefore = { ...stateBefore.elements.get(idC)! };
          const connBCBefore = { ...stateBefore.connectors.get(connBC)! };

          // Delete connector A->B
          useDiagramStore.getState().removeConnector(connAB);

          const stateAfter = useDiagramStore.getState();

          // Deleted connector is removed
          expect(stateAfter.connectors.has(connAB)).toBe(false);

          // Other connector is preserved
          expect(stateAfter.connectors.has(connBC)).toBe(true);
          const connBCAfter = stateAfter.connectors.get(connBC)!;
          expect(connBCAfter.sourceId).toBe(connBCBefore.sourceId);
          expect(connBCAfter.targetId).toBe(connBCBefore.targetId);
          expect(connBCAfter.connectionType).toBe(connBCBefore.connectionType);

          // All elements remain unchanged (same count, same data)
          expect(stateAfter.elements.size).toBe(elementCountBefore);

          const elAAfter = stateAfter.elements.get(idA)!;
          expect(elAAfter.serviceType).toBe(elABefore.serviceType);
          expect(elAAfter.name).toBe(elABefore.name);
          expect(elAAfter.position.x).toBe(elABefore.position.x);
          expect(elAAfter.position.y).toBe(elABefore.position.y);

          const elBAfter = stateAfter.elements.get(idB)!;
          expect(elBAfter.serviceType).toBe(elBBefore.serviceType);
          expect(elBAfter.name).toBe(elBBefore.name);
          expect(elBAfter.position.x).toBe(elBBefore.position.x);
          expect(elBAfter.position.y).toBe(elBBefore.position.y);

          const elCAfter = stateAfter.elements.get(idC)!;
          expect(elCAfter.serviceType).toBe(elCBefore.serviceType);
          expect(elCAfter.name).toBe(elCBefore.name);
          expect(elCAfter.position.x).toBe(elCBefore.position.x);
          expect(elCAfter.position.y).toBe(elCBefore.position.y);
        }
      ),
      { numRuns: 100 }
    );
  });
});
