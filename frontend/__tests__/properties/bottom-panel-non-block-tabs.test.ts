import fc from 'fast-check';
import { getTabsForObject } from '@/components/config/BottomPanel';
import { lineObjectWithoutIdArbitrary, geometricObjectWithoutIdArbitrary } from './arbitraries';

// Feature: bottom-panel-redesign, Property 9: Non-architecture-block tab set
// **Validates: Requirements 5.3**
describe('Property 9: Non-architecture-block tab set', () => {
  test('for any line object, getTabsForObject returns exactly [Visual]', () => {
    fc.assert(
      fc.property(
        lineObjectWithoutIdArbitrary(),
        (linePayload) => {
          const line = { ...linePayload, id: 'test-id', zIndex: 0 };
          const tabs = getTabsForObject(line);

          expect(tabs).toEqual(['Visual']);
        }
      ),
      { numRuns: 100 }
    );
  });

  test('for any geometric object, getTabsForObject returns exactly [Visual]', () => {
    fc.assert(
      fc.property(
        geometricObjectWithoutIdArbitrary(),
        (geoPayload) => {
          const geo = { ...geoPayload, id: 'test-id', zIndex: 0 };
          const tabs = getTabsForObject(geo);

          expect(tabs).toEqual(['Visual']);
        }
      ),
      { numRuns: 100 }
    );
  });
});
