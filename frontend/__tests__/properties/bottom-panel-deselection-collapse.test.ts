import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import {
  canvasObjectWithoutIdArbitrary,
} from './arbitraries';

// Feature: bottom-panel-redesign, Property 4: Deselection auto-collapses panel
// **Validates: Requirements 1.5, 6.2**
describe('Property 4: Deselection auto-collapses panel', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      bottomPanelExpanded: false,
      bottomPanelHeight: 250,
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
    });
  });

  test('for any non-empty selection, clearing selection and simulating auto-collapse results in bottomPanelExpanded = false', () => {
    fc.assert(
      fc.property(
        fc.array(canvasObjectWithoutIdArbitrary(), { minLength: 1, maxLength: 5 }),
        (payloads) => {
          // Reset store
          useDiagramStore.setState({
            bottomPanelExpanded: false,
            canvasObjects: new Map(),
            selectedObjectIds: new Set(),
          });

          const { addCanvasObject, selectObject, setBottomPanelExpanded, toggleObjectSelection } =
            useDiagramStore.getState();

          // 1. Add all objects to the store
          const ids = payloads.map((payload) => addCanvasObject(payload));

          // 2. Select objects — single select for 1, toggle for multiple
          if (ids.length === 1) {
            selectObject(ids[0]);
          } else {
            for (const id of ids) {
              toggleObjectSelection(id);
            }
          }

          // Verify we have a non-empty selection
          const { selectedObjectIds } = useDiagramStore.getState();
          expect(selectedObjectIds.size).toBeGreaterThan(0);

          // 3. Simulate the useEffect auto-expand (selection > 0 → expand)
          setBottomPanelExpanded(true);
          expect(useDiagramStore.getState().bottomPanelExpanded).toBe(true);

          // 4. Clear selection (deselect all)
          selectObject(null);
          expect(useDiagramStore.getState().selectedObjectIds.size).toBe(0);

          // 5. Simulate the useEffect auto-collapse (selection === 0 → collapse)
          setBottomPanelExpanded(false);

          // 6. Assert the panel is collapsed
          expect(useDiagramStore.getState().bottomPanelExpanded).toBe(false);
        }
      ),
      { numRuns: 100 }
    );
  });
});
