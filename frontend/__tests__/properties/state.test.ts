import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import {
  serviceTypeArbitrary,
  pointArbitrary,
  resourceConfigArbitrary,
  operationArbitrary,
} from './arbitraries';

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

function resetStore() {
  useDiagramStore.setState({
    elements: new Map(),
    connectors: new Map(),
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
}

// Feature: diagram-editor-frontend, Property 8: Config update reflects in element state
// **Validates: Requirements 5.7**
describe('Property 8: Config update reflects in element state', () => {
  test('updateElementConfig merges correctly preserving other fields', () => {
    fc.assert(
      fc.property(
        serviceTypeArbitrary(),
        pointArbitrary(),
        resourceConfigArbitrary(),
        resourceConfigArbitrary(),
        (serviceType, position, initialConfig, partialUpdate) => {
          resetStore();

          // Create an element and set initial config
          const store = useDiagramStore.getState();
          const id = store.addElement(serviceType, position);
          useDiagramStore.getState().updateElementConfig(id, initialConfig);

          // Snapshot the config after initial set
          const configBefore = {
            ...useDiagramStore.getState().elements.get(id)!.config,
          };

          // Filter out undefined values from the partial update to get only meaningful updates
          const meaningfulUpdate: Record<string, unknown> = {};
          for (const [key, value] of Object.entries(partialUpdate)) {
            if (value !== undefined) {
              meaningfulUpdate[key] = value;
            }
          }

          // Apply partial update (only meaningful fields)
          useDiagramStore.getState().updateElementConfig(id, meaningfulUpdate as Partial<typeof partialUpdate>);

          const configAfter = useDiagramStore.getState().elements.get(id)!.config;

          // All fields from the meaningful update should be present in the result
          for (const [key, value] of Object.entries(meaningfulUpdate)) {
            expect((configAfter as Record<string, unknown>)[key]).toBe(value);
          }

          // Fields NOT in the meaningful update should be preserved from before
          for (const [key, value] of Object.entries(configBefore)) {
            if (!(key in meaningfulUpdate)) {
              expect((configAfter as Record<string, unknown>)[key]).toBe(value);
            }
          }

          // Element's non-config fields should be unchanged
          const element = useDiagramStore.getState().elements.get(id)!;
          expect(element.serviceType).toBe(serviceType);
          expect(element.position.x).toBe(position.x);
          expect(element.position.y).toBe(position.y);
        }
      ),
      { numRuns: 100 }
    );
  });
});


// Feature: diagram-editor-frontend, Property 11: State consistency invariant
// **Validates: Requirements 9.1**
describe('Property 11: State consistency invariant', () => {
  test('after any sequence of operations, all connector refs point to existing elements and all IDs are unique', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 3, max: 15 }),
        (numOps) => {
          resetStore();

          // Seed with a couple of elements so operations have something to work with
          const store = useDiagramStore.getState();
          store.addElement('lambda', { x: 0, y: 0 });
          useDiagramStore.getState().addElement('s3', { x: 100, y: 100 });

          // Apply a sequence of random operations
          for (let i = 0; i < numOps; i++) {
            const state = useDiagramStore.getState();
            const elementIds = Array.from(state.elements.keys());
            const connectorIds = Array.from(state.connectors.keys());

            // Generate and apply one random operation
            const opArb = operationArbitrary(elementIds, connectorIds);
            const op = fc.sample(opArb, 1)[0];

            try {
              const s = useDiagramStore.getState();
              const payload = op.payload as Record<string, unknown>;

              switch (op.type) {
                case 'addElement':
                  s.addElement(
                    payload.serviceType as Parameters<typeof s.addElement>[0],
                    payload.position as Parameters<typeof s.addElement>[1]
                  );
                  break;
                case 'moveElement':
                  s.updateElementPosition(
                    payload.id as string,
                    payload.position as Parameters<typeof s.updateElementPosition>[1]
                  );
                  break;
                case 'deleteElement':
                  s.removeElement(payload.id as string);
                  break;
                case 'updateConfig':
                  s.updateElementConfig(
                    payload.id as string,
                    payload.config as Parameters<typeof s.updateElementConfig>[1]
                  );
                  break;
                case 'addConnector':
                  s.addConnector(
                    payload.sourceId as string,
                    payload.targetId as string
                  );
                  break;
                case 'deleteConnector':
                  s.removeConnector(payload.id as string);
                  break;
              }
            } catch {
              // Some operations may throw (e.g., addConnector with invalid refs after deletion)
              // This is expected — we just skip them
            }
          }

          // Verify state consistency invariants
          const finalState = useDiagramStore.getState();

          // All connector refs point to existing elements
          for (const [, conn] of finalState.connectors) {
            expect(finalState.elements.has(conn.sourceId)).toBe(true);
            expect(finalState.elements.has(conn.targetId)).toBe(true);
          }

          // All element IDs are unique (Map guarantees this, but verify size matches)
          const elementIds = Array.from(finalState.elements.keys());
          expect(new Set(elementIds).size).toBe(elementIds.length);

          // All connector IDs are unique
          const connectorIds = Array.from(finalState.connectors.keys());
          expect(new Set(connectorIds).size).toBe(connectorIds.length);

          // No connector has sourceId === targetId
          for (const [, conn] of finalState.connectors) {
            expect(conn.sourceId).not.toBe(conn.targetId);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});


/** Helper: serialize elements and connectors Maps to sorted arrays for deep comparison */
function snapshotState() {
  const state = useDiagramStore.getState();
  const elements = Array.from(state.elements.values())
    .map((el) => ({ ...el, config: { ...el.config }, position: { ...el.position } }))
    .sort((a, b) => a.id.localeCompare(b.id));
  const connectors = Array.from(state.connectors.values())
    .map((c) => ({ ...c }))
    .sort((a, b) => a.id.localeCompare(b.id));
  return { elements, connectors };
}

// Feature: diagram-editor-frontend, Property 12: Undo/redo round-trip
// **Validates: Requirements 9.3, 9.4**
describe('Property 12: Undo/redo round-trip', () => {
  test('action + undo restores original state; undo + redo restores post-action state', () => {
    fc.assert(
      fc.property(
        serviceTypeArbitrary(),
        serviceTypeArbitrary(),
        serviceTypeArbitrary(),
        pointArbitrary(),
        pointArbitrary(),
        pointArbitrary(),
        fc.constantFrom('addElement', 'moveElement', 'deleteElement', 'addConnector', 'updateConfig'),
        (type1, type2, type3, pos1, pos2, pos3, mutationType) => {
          resetStore();

          // Build initial state with some elements
          const store = useDiagramStore.getState();
          const idA = store.addElement(type1, pos1);
          const idB = useDiagramStore.getState().addElement(type2, pos2);

          // Clear undo stack so we start fresh for the test
          useDiagramStore.setState({ _undoStack: [], _redoStack: [], canUndo: false, canRedo: false });

          // Snapshot pre-mutation state
          const preMutation = snapshotState();

          // Perform a single mutation
          try {
            const s = useDiagramStore.getState();
            switch (mutationType) {
              case 'addElement':
                s.addElement(type3, pos3);
                break;
              case 'moveElement':
                s.updateElementPosition(idA, pos3);
                break;
              case 'deleteElement':
                s.removeElement(idA);
                break;
              case 'addConnector':
                s.addConnector(idA, idB);
                break;
              case 'updateConfig':
                s.updateElementConfig(idA, { handler: 'test.handler', runtime: 'nodejs20.x' });
                break;
            }
          } catch {
            // If mutation throws (shouldn't for these cases), skip
            return;
          }

          // Snapshot post-mutation state
          const postMutation = snapshotState();

          // Undo → should restore pre-mutation state
          useDiagramStore.getState().undo();
          const afterUndo = snapshotState();
          expect(afterUndo).toEqual(preMutation);

          // Redo → should restore post-mutation state
          useDiagramStore.getState().redo();
          const afterRedo = snapshotState();
          expect(afterRedo).toEqual(postMutation);
        }
      ),
      { numRuns: 100 }
    );
  });
});
