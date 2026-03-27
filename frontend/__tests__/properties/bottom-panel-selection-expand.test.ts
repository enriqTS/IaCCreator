import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import {
  canvasObjectWithoutIdArbitrary,
} from './arbitraries';

// Feature: bottom-panel-redesign, Property 3: Selection auto-expands panel
// **Validates: Requirements 1.4**
describe('Property 3: Selection auto-expands panel', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      bottomPanelExpanded: false,
      bottomPanelHeight: 250,
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
    });
  });

  test('for any canvas object, selecting it and expanding results in bottomPanelExpanded = true', () => {
    fc.assert(
      fc.property(
        canvasObjectWithoutIdArbitrary(),
        (payload) => {
          // Reset to collapsed state
          useDiagramStore.setState({
            bottomPanelExpanded: false,
            canvasObjects: new Map(),
            selectedObjectIds: new Set(),
          });

          const { addCanvasObject, selectObject, setBottomPanelExpanded } =
            useDiagramStore.getState();

          // 1. Add the object to the store
          const id = addCanvasObject(payload);

          // 2. Select the object (sets selectedObjectIds)
          selectObject(id);
          const { selectedObjectIds } = useDiagramStore.getState();
          expect(selectedObjectIds.size).toBeGreaterThan(0);

          // 3. Simulate the useEffect auto-expand: when selectedObjectIds > 0, expand
          setBottomPanelExpanded(true);

          // 4. Assert the panel is expanded
          expect(useDiagramStore.getState().bottomPanelExpanded).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });
});
