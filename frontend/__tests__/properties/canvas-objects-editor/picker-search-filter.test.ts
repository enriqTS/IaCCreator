import fc from 'fast-check';
import { describe, it, expect } from 'vitest';
import { smartSearch } from '@/components/toolbar/ObjectPickerMenu';
import type { PickerItem } from '@/components/toolbar/ObjectPickerMenu';
import type { Tool } from '@/types/diagram';

/**
 * Feature: canvas-objects-editor, Property 10: Object picker search filters correctly
 * **Validates: Requirements 7.3**
 */
describe('Property 10: Object picker search filters correctly', () => {
  // Generator for a random picker item
  const pickerItemArb: fc.Arbitrary<PickerItem> = fc.record({
    name: fc.string({ minLength: 1, maxLength: 40 }),
    category: fc.constantFrom('AWS: Compute', 'Shapes', 'UML', 'Text', 'Lines & Arrows'),
    tool: fc.constant('pointer' as Tool),
  });

  it('filtered results contain only items whose name includes the search term (case-insensitive), and every matching item appears', () => {
    fc.assert(
      fc.property(
        fc.array(pickerItemArb, { minLength: 0, maxLength: 30 }),
        fc.string({ minLength: 0, maxLength: 20 }),
        (items, searchTerm) => {
          const result = smartSearch(items, searchTerm, {});
          const lower = searchTerm.toLowerCase();
          const isEmptySearch = !searchTerm || searchTerm.trim() === '';

          if (isEmptySearch) {
            // Empty search returns all items
            expect(result.length).toBe(items.length);
            return;
          }

          // Every result item's name must contain the search term (case-insensitive)
          for (const item of result) {
            expect(item.name.toLowerCase()).toContain(lower);
          }

          // Every item in the original list whose name contains the search term must be in the result
          const expectedMatches = items.filter((item) =>
            item.name.toLowerCase().includes(lower)
          );
          expect(result.length).toBe(expectedMatches.length);

          // Verify exact set equality by checking all expected items are present
          for (const expected of expectedMatches) {
            expect(result).toContainEqual(expected);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
