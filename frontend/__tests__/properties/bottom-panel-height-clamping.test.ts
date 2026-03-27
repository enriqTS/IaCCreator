import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import { MIN_PANEL_HEIGHT, MAX_PANEL_HEIGHT_RATIO } from '@/components/config/panel-constants';

// Feature: bottom-panel-redesign, Property 5: Height clamping within bounds
// **Validates: Requirements 2.4, 2.5**
describe('Property 5: Height clamping within bounds', () => {
  const VIEWPORT_HEIGHT = window.innerHeight; // 768 in jsdom
  const MAX_HEIGHT = MAX_PANEL_HEIGHT_RATIO * VIEWPORT_HEIGHT;

  beforeEach(() => {
    useDiagramStore.setState({
      bottomPanelExpanded: false,
      bottomPanelHeight: 250,
    });
  });

  test('any height value is clamped to [MIN_PANEL_HEIGHT, MAX_PANEL_HEIGHT_RATIO × viewportHeight]', () => {
    fc.assert(
      fc.property(
        fc.double({ min: -10000, max: 10000, noNaN: true, noDefaultInfinity: true }),
        (requestedHeight) => {
          const { setBottomPanelHeight } = useDiagramStore.getState();
          setBottomPanelHeight(requestedHeight);

          const { bottomPanelHeight } = useDiagramStore.getState();
          expect(bottomPanelHeight).toBeGreaterThanOrEqual(MIN_PANEL_HEIGHT);
          expect(bottomPanelHeight).toBeLessThanOrEqual(MAX_HEIGHT);
        }
      ),
      { numRuns: 100 }
    );
  });

  test('values below MIN_PANEL_HEIGHT are clamped up to MIN_PANEL_HEIGHT', () => {
    fc.assert(
      fc.property(
        fc.double({ min: -10000, max: MIN_PANEL_HEIGHT - 1, noNaN: true, noDefaultInfinity: true }),
        (requestedHeight) => {
          const { setBottomPanelHeight } = useDiagramStore.getState();
          setBottomPanelHeight(requestedHeight);

          const { bottomPanelHeight } = useDiagramStore.getState();
          expect(bottomPanelHeight).toBe(MIN_PANEL_HEIGHT);
        }
      ),
      { numRuns: 100 }
    );
  });

  test('values above MAX_HEIGHT are clamped down to MAX_HEIGHT', () => {
    fc.assert(
      fc.property(
        fc.double({ min: MAX_HEIGHT + 1, max: 10000, noNaN: true, noDefaultInfinity: true }),
        (requestedHeight) => {
          const { setBottomPanelHeight } = useDiagramStore.getState();
          setBottomPanelHeight(requestedHeight);

          const { bottomPanelHeight } = useDiagramStore.getState();
          expect(bottomPanelHeight).toBe(MAX_HEIGHT);
        }
      ),
      { numRuns: 100 }
    );
  });

  test('values within valid range are stored as-is', () => {
    fc.assert(
      fc.property(
        fc.double({ min: MIN_PANEL_HEIGHT, max: MAX_HEIGHT, noNaN: true, noDefaultInfinity: true }),
        (requestedHeight) => {
          const { setBottomPanelHeight } = useDiagramStore.getState();
          setBottomPanelHeight(requestedHeight);

          const { bottomPanelHeight } = useDiagramStore.getState();
          expect(bottomPanelHeight).toBe(requestedHeight);
        }
      ),
      { numRuns: 100 }
    );
  });
});
