import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { serviceTypeArbitrary, pointArbitrary } from './arbitraries';

beforeEach(() => {
  useDiagramStore.setState({
    connectors: new Map(),
    canvasObjects: new Map(),
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
});

function addBlock(serviceType: string, position: { x: number; y: number }) {
  return useDiagramStore.getState().addCanvasObject({
    objectType: 'architecture-block',
    serviceType: serviceType as import('@/types/diagram').ServiceType,
    name: `${serviceType}-block`,
    position,
    config: {},
    terraformVariables: {},
    visualConfig: { width: 80, height: 80 },
  });
}

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
            connectors: new Map(),
            canvasObjects: new Map(),
            _undoStack: [],
            _redoStack: [],
            canUndo: false,
            canRedo: false,
          });

          // Create two architecture blocks
          const id1 = addBlock(type1, pos1);
          const id2 = addBlock(type2, pos2);

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

          // Connected canvas objects remain unchanged
          const obj1After = stateAfter.canvasObjects.get(id1)!;
          const obj2After = stateAfter.canvasObjects.get(id2)!;

          expect(obj1After.objectType).toBe('architecture-block');
          expect(obj2After.objectType).toBe('architecture-block');
        }
      ),
      { numRuns: 100 }
    );
  });
});

// Feature: diagram-editor-frontend, Property 7: Connector deletion preserves elements
// **Validates: Requirements 4.4**
describe('Property 7: Connector deletion preserves canvas objects', () => {
  test('deleting a connector removes only that connector; all canvas objects unchanged', () => {
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
            connectors: new Map(),
            canvasObjects: new Map(),
            _undoStack: [],
            _redoStack: [],
            canUndo: false,
            canRedo: false,
          });

          // Create three architecture blocks and two connectors
          const idA = addBlock(type1, pos1);
          const idB = addBlock(type2, pos2);
          const idC = addBlock(type3, pos3);

          const connAB = useDiagramStore.getState().addConnector(idA, idB);
          const connBC = useDiagramStore.getState().addConnector(idB, idC);

          // Snapshot state before deletion
          const stateBefore = useDiagramStore.getState();
          const objectCountBefore = stateBefore.canvasObjects.size;
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

          // All canvas objects remain (same count)
          expect(stateAfter.canvasObjects.size).toBe(objectCountBefore);
          expect(stateAfter.canvasObjects.has(idA)).toBe(true);
          expect(stateAfter.canvasObjects.has(idB)).toBe(true);
          expect(stateAfter.canvasObjects.has(idC)).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });
});
