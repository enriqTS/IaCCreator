import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { MIN_PANEL_HEIGHT, MAX_PANEL_HEIGHT_RATIO } from '@/components/config/panel-constants';

// Feature: bottom-panel-redesign, Property 2: Toggle collapses expanded panel
// **Validates: Requirements 1.3**
describe('Property 2: Toggle collapses expanded panel', () => {
  const VIEWPORT_HEIGHT = window.innerHeight; // 768 in jsdom
  const MAX_HEIGHT = MAX_PANEL_HEIGHT_RATIO * VIEWPORT_HEIGHT;

  beforeEach(() => {
    useDiagramStore.setState({
      bottomPanelExpanded: false,
      bottomPanelHeight: 250,
    });
  });

  test('for any expanded panel state with any valid height, toggling results in collapsed', () => {
    fc.assert(
      fc.property(
        fc.double({ min: MIN_PANEL_HEIGHT, max: MAX_HEIGHT, noNaN: true, noDefaultInfinity: true }),
        (height) => {
          // Set up an expanded panel with the generated height
          useDiagramStore.setState({
            bottomPanelExpanded: true,
            bottomPanelHeight: height,
          });

          // Toggle the panel
          const { toggleBottomPanel } = useDiagramStore.getState();
          toggleBottomPanel();

          // Assert panel is now collapsed
          const { bottomPanelExpanded } = useDiagramStore.getState();
          expect(bottomPanelExpanded).toBe(false);
        }
      ),
      { numRuns: 100 }
    );
  });
});
