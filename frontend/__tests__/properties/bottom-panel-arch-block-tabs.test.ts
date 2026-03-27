import fc from 'fast-check';
import { getTabsForObject } from '@/components/config/BottomPanel';
import { architectureBlockWithoutIdArbitrary } from './arbitraries';

// Feature: bottom-panel-redesign, Property 8: Architecture block tab set
// **Validates: Requirements 5.1, 5.2**
describe('Property 8: Architecture block tab set', () => {
  test('for any architecture-block, getTabsForObject returns exactly [Variables, Visual] and never Terraform', () => {
    fc.assert(
      fc.property(
        architectureBlockWithoutIdArbitrary(),
        (blockPayload) => {
          // Construct a full CanvasObject by adding id and zIndex
          const block = { ...blockPayload, id: 'test-id', zIndex: 0 };
          const tabs = getTabsForObject(block);

          // Tabs should be exactly ['Variables', 'Visual']
          expect(tabs).toEqual(['Variables', 'Visual']);

          // Tabs should NOT contain 'Terraform'
          expect(tabs).not.toContain('Terraform');
        }
      ),
      { numRuns: 100 }
    );
  });
});
