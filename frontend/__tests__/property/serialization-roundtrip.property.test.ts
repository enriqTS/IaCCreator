/**
 * Property-based test: Z-order serialization round trip
 *
 * **Validates: Requirements 5.7, 8.8**
 *
 * Property 4: Serializing and deserializing preserves zIndex values and group definitions.
 */
import { describe, it, beforeEach } from 'vitest';
import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { canvasObjectWithoutIdArbitrary } from '../properties/arbitraries';

describe('Serialization Round Trip Property', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
      objectGroups: new Map(),
      elements: new Map(),
      connectors: new Map(),
      viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
      projectName: '',
      environments: [],
    });
  });

  it('Property 4: serializing and deserializing preserves zIndex values and group definitions', () => {
    /**
     * **Validates: Requirements 5.7, 8.8**
     *
     * Strategy:
     * 1. Generate a random set of canvas objects (with various zIndex values)
     * 2. Optionally group some of them
     * 3. Serialize the diagram state using serializeDiagramState()
     * 4. Load it back using loadDiagramState()
     * 5. Verify that all zIndex values are preserved exactly
     * 6. Verify that all group definitions (id, name, memberIds) are preserved exactly
     * 7. Verify that groupId references on canvas objects are preserved
     */
    fc.assert(
      fc.property(
        fc.array(canvasObjectWithoutIdArbitrary(), { minLength: 1, maxLength: 8 }).chain((payloads) =>
          // Boolean flag: whether to create a group from the first 2+ objects
          fc.boolean().map((shouldGroup) => ({ payloads, shouldGroup })),
        ),
        ({ payloads, shouldGroup }) => {
          const store = useDiagramStore.getState();
          const addedIds: string[] = [];

          // Add all canvas objects
          for (const payload of payloads) {
            const id = store.addCanvasObject(payload);
            addedIds.push(id);
          }

          // Optionally group the first 2 objects
          if (shouldGroup && addedIds.length >= 2) {
            // Select first two objects and group them
            useDiagramStore.getState().selectObject(addedIds[0]);
            useDiagramStore.getState().toggleObjectSelection(addedIds[1]);
            useDiagramStore.getState().groupSelectedObjects();
          }

          // Capture pre-serialization state
          const preState = useDiagramStore.getState();
          const preObjects = new Map(preState.canvasObjects);
          const preGroups = new Map(preState.objectGroups);

          // Serialize
          const serialized = useDiagramStore.getState().serializeDiagramState();

          // Reset store completely
          useDiagramStore.setState({
            canvasObjects: new Map(),
            selectedObjectIds: new Set(),
            objectGroups: new Map(),
            elements: new Map(),
            connectors: new Map(),
            viewport: { offsetX: 0, offsetY: 0, scale: 1.0 },
            projectName: '',
            environments: [],
          });

          // Load from serialized state
          useDiagramStore.getState().loadDiagramState(serialized);

          const postState = useDiagramStore.getState();
          const postObjects = postState.canvasObjects;
          const postGroups = postState.objectGroups;

          // Verify same number of canvas objects
          if (postObjects.size !== preObjects.size) return false;

          // Verify all zIndex values are preserved exactly
          for (const [id, preObj] of preObjects) {
            const postObj = postObjects.get(id);
            if (!postObj) return false;
            if (postObj.zIndex !== preObj.zIndex) return false;
          }

          // Verify all groupId references on canvas objects are preserved
          for (const [id, preObj] of preObjects) {
            const postObj = postObjects.get(id)!;
            if (preObj.groupId !== postObj.groupId) return false;
          }

          // Verify same number of groups
          if (postGroups.size !== preGroups.size) return false;

          // Verify all group definitions (id, name, memberIds) are preserved exactly
          for (const [groupId, preGroup] of preGroups) {
            const postGroup = postGroups.get(groupId);
            if (!postGroup) return false;
            if (postGroup.id !== preGroup.id) return false;
            if (postGroup.name !== preGroup.name) return false;
            if (postGroup.memberIds.length !== preGroup.memberIds.length) return false;
            // memberIds should contain the same elements (order may differ)
            const preSorted = [...preGroup.memberIds].sort();
            const postSorted = [...postGroup.memberIds].sort();
            for (let i = 0; i < preSorted.length; i++) {
              if (preSorted[i] !== postSorted[i]) return false;
            }
          }

          return true;
        },
      ),
      { numRuns: 200 },
    );
  });
});
