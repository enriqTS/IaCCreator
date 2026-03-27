import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { canvasObjectWithoutIdArbitrary } from './arbitraries';

// Feature: bottom-panel-redesign, Property 10: Multi-selection count
// **Validates: Requirements 6.1**
describe('Property 10: Multi-selection count', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      bottomPanelExpanded: false,
      bottomPanelHeight: 250,
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
    });
  });

  test('for any set of 2+ canvas objects added and selected, selectedObjectIds.size equals the number of objects selected', () => {
    fc.assert(
      fc.property(
        fc.array(canvasObjectWithoutIdArbitrary(), { minLength: 2, maxLength: 10 }),
        (payloads) => {
          // Reset store
          useDiagramStore.setState({
            bottomPanelExpanded: false,
            canvasObjects: new Map(),
            selectedObjectIds: new Set(),
          });

          const { addCanvasObject, toggleObjectSelection } = useDiagramStore.getState();

          // 1. Add all objects to the store
          const ids = payloads.map((payload) => addCanvasObject(payload));

          // 2. Select all objects via toggleObjectSelection
          for (const id of ids) {
            toggleObjectSelection(id);
          }

          // 3. Assert selectedObjectIds.size matches the number of objects selected
          const { selectedObjectIds } = useDiagramStore.getState();
          expect(selectedObjectIds.size).toBe(ids.length);
        }
      ),
      { numRuns: 100 }
    );
  });
});
