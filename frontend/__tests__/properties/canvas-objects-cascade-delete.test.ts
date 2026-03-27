import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { serviceTypeArbitrary, pointArbitrary } from './arbitraries';
import type { ArchitectureBlock, Connector } from '@/types/diagram';
import { DEFAULT_BLOCK_VISUAL } from '@/types/diagram';
import { getDefaultVariables } from '@/types/terraform-variables';

function resetStore() {
  useDiagramStore.setState({
    canvasObjects: new Map(),
    connectors: new Map(),
    elements: new Map(),
    selectedObjectIds: new Set(),
    _undoStack: [],
    _redoStack: [],
    canUndo: false,
    canRedo: false,
  });
}

/**
 * Helper: adds an element + corresponding architecture block canvas object with the same ID.
 * Connectors validate against the `elements` Map, so we must add elements first.
 */
function addBlockWithElement(
  serviceType: 'lambda' | 's3' | 'api-gateway' | 'dynamodb' | 'iam' | 'cloudwatch',
  position: { x: number; y: number },
  name: string,
): string {
  const store = useDiagramStore.getState();
  // addElement creates an entry in the elements Map (needed for connector validation)
  const id = store.addElement(serviceType, position);

  // Add a corresponding canvas object with the same ID
  useDiagramStore.setState((state) => {
    const next = new Map(state.canvasObjects);
    next.set(id, {
      id,
      objectType: 'architecture-block',
      serviceType,
      name,
      position,
      config: {},
      terraformVariables: getDefaultVariables(serviceType),
      visualConfig: { ...DEFAULT_BLOCK_VISUAL },
    } as ArchitectureBlock);
    return { canvasObjects: next };
  });

  return id;
}

// Feature: canvas-objects-editor, Property 10: Architecture block deletion cascades to connectors
// **Validates: Requirements 11.3**
describe('Property 10: Architecture block deletion cascades to connectors', () => {
  beforeEach(resetStore);

  test('deleting an architecture block removes all connectors referencing it', () => {
    fc.assert(
      fc.property(
        serviceTypeArbitrary(),
        serviceTypeArbitrary(),
        pointArbitrary(),
        pointArbitrary(),
        fc.constantFrom('triggers', 'reads_from', 'writes_to', 'invokes'),
        (serviceType1, serviceType2, pos1, pos2, connType) => {
          resetStore();

          // Create two blocks with elements
          const blockId1 = addBlockWithElement(serviceType1, pos1, 'block-1');
          const blockId2 = addBlockWithElement(serviceType2, pos2, 'block-2');

          // Add a connector between them
          const connId = useDiagramStore.getState().addConnector(blockId1, blockId2, connType);

          // Verify connector exists
          expect(useDiagramStore.getState().connectors.has(connId)).toBe(true);

          // Delete the source block via removeCanvasObject
          useDiagramStore.getState().removeCanvasObject(blockId1);

          const state = useDiagramStore.getState();

          // The block is removed
          expect(state.canvasObjects.has(blockId1)).toBe(false);

          // The connector referencing the deleted block is also removed
          expect(state.connectors.has(connId)).toBe(false);

          // No orphaned connectors remain that reference the deleted block
          for (const conn of state.connectors.values()) {
            expect(conn.sourceId).not.toBe(blockId1);
            expect(conn.targetId).not.toBe(blockId1);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  test('deleting a block with multiple connectors removes all of them', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 2, max: 5 }),
        serviceTypeArbitrary(),
        pointArbitrary(),
        (numOtherBlocks, deletedServiceType, deletedPos) => {
          resetStore();

          // Create the block to be deleted
          const deletedBlockId = addBlockWithElement(deletedServiceType, deletedPos, 'to-delete');

          // Create other blocks and connectors referencing the deleted block
          const otherBlockIds: string[] = [];
          const connectorIds: string[] = [];

          for (let i = 0; i < numOtherBlocks; i++) {
            const otherId = addBlockWithElement('lambda', { x: i * 100, y: 0 }, `other-${i}`);
            otherBlockIds.push(otherId);

            // Alternate: some connectors where deleted block is source, some where it's target
            const connId = i % 2 === 0
              ? useDiagramStore.getState().addConnector(deletedBlockId, otherId)
              : useDiagramStore.getState().addConnector(otherId, deletedBlockId);
            connectorIds.push(connId);
          }

          // Verify all connectors exist before deletion
          for (const cid of connectorIds) {
            expect(useDiagramStore.getState().connectors.has(cid)).toBe(true);
          }

          // Delete the block
          useDiagramStore.getState().removeCanvasObject(deletedBlockId);

          const state = useDiagramStore.getState();

          // All connectors referencing the deleted block are gone
          for (const cid of connectorIds) {
            expect(state.connectors.has(cid)).toBe(false);
          }

          // No orphaned connectors reference the deleted block
          for (const conn of state.connectors.values()) {
            expect(conn.sourceId).not.toBe(deletedBlockId);
            expect(conn.targetId).not.toBe(deletedBlockId);
          }

          // Other blocks still exist
          for (const otherId of otherBlockIds) {
            expect(state.canvasObjects.has(otherId)).toBe(true);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  test('connectors not referencing the deleted block remain intact', () => {
    fc.assert(
      fc.property(
        serviceTypeArbitrary(),
        serviceTypeArbitrary(),
        serviceTypeArbitrary(),
        pointArbitrary(),
        pointArbitrary(),
        pointArbitrary(),
        (st1, st2, st3, pos1, pos2, pos3) => {
          resetStore();

          // Create three blocks
          const blockA = addBlockWithElement(st1, pos1, 'block-a');
          const blockB = addBlockWithElement(st2, pos2, 'block-b');
          const blockC = addBlockWithElement(st3, pos3, 'block-c');

          // Connector between A and B (will be cascade-deleted when A is removed)
          const connAB = useDiagramStore.getState().addConnector(blockA, blockB);
          // Connector between B and C (should survive deletion of A)
          const connBC = useDiagramStore.getState().addConnector(blockB, blockC);

          // Delete block A
          useDiagramStore.getState().removeCanvasObject(blockA);

          const state = useDiagramStore.getState();

          // Connector A→B is removed
          expect(state.connectors.has(connAB)).toBe(false);

          // Connector B→C is still present
          expect(state.connectors.has(connBC)).toBe(true);
          const survivingConn = state.connectors.get(connBC)!;
          expect(survivingConn.sourceId).toBe(blockB);
          expect(survivingConn.targetId).toBe(blockC);
        },
      ),
      { numRuns: 100 },
    );
  });
});
