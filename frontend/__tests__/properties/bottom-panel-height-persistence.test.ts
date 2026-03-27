import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { MIN_PANEL_HEIGHT, MAX_PANEL_HEIGHT_RATIO } from '@/components/config/panel-constants';

// Feature: bottom-panel-redesign, Property 1: Height persistence round trip
// **Validates: Requirements 1.2, 2.6, 7.1, 7.2**
describe('Property 1: Height persistence round trip', () => {
  const VIEWPORT_HEIGHT = window.innerHeight; // 768 in jsdom
  const MAX_HEIGHT = MAX_PANEL_HEIGHT_RATIO * VIEWPORT_HEIGHT;

  beforeEach(() => {
    useDiagramStore.setState({
      bottomPanelExpanded: false,
      bottomPanelHeight: 250,
    });
  });

  test('set height → collapse → expand → height matches original', () => {
    fc.assert(
      fc.property(
        fc.double({ min: MIN_PANEL_HEIGHT, max: MAX_HEIGHT, noNaN: true, noDefaultInfinity: true }),
        (height) => {
          const store = useDiagramStore.getState();

          // 1. Set height to a valid value
          store.setBottomPanelHeight(height);
          expect(useDiagramStore.getState().bottomPanelHeight).toBe(height);

          // 2. Collapse the panel
          store.setBottomPanelExpanded(false);
          expect(useDiagramStore.getState().bottomPanelExpanded).toBe(false);

          // 3. Expand the panel
          store.setBottomPanelExpanded(true);
          expect(useDiagramStore.getState().bottomPanelExpanded).toBe(true);

          // 4. Assert height is preserved
          expect(useDiagramStore.getState().bottomPanelHeight).toBe(height);
        }
      ),
      { numRuns: 100 }
    );
  });
});
