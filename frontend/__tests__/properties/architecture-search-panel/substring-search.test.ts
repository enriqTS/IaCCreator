import fc from 'fast-check';
import { smartSearch } from '@/components/toolbar/ObjectPickerMenu';
import type { PickerItem } from '@/components/toolbar/ObjectPickerMenu';

// Feature: architecture-search-panel, Property 1: Substring search inclusion
// **Validates: Requirements 2.6**

/**
 * Arbitrary that generates a PickerItem with a given name.
 */
function pickerItemWithName(name: string): PickerItem {
  return {
    name,
    category: 'Shapes',
    tool: 'pointer',
  };
}

/**
 * Arbitrary that generates a random PickerItem with a non-empty name.
 */
function arbitraryPickerItem(): fc.Arbitrary<PickerItem> {
  return fc
    .string({ minLength: 1, maxLength: 40 })
    .filter((s) => s.trim().length > 0)
    .map((name) => pickerItemWithName(name));
}

/**
 * Given a non-empty string, generate a random contiguous substring (length > 0).
 */
function arbitrarySubstring(name: string): fc.Arbitrary<string> {
  return fc
    .integer({ min: 0, max: name.length - 1 })
    .chain((start) =>
      fc
        .integer({ min: 1, max: name.length - start })
        .map((len) => name.slice(start, start + len))
    );
}

describe('Property 1: Substring search inclusion', () => {
  test('smartSearch with any contiguous substring of an item name returns that item in results', () => {
    fc.assert(
      fc.property(
        // Generate a target item with a non-empty name
        arbitraryPickerItem().chain((targetItem) =>
          // Generate a contiguous substring of that item's name
          arbitrarySubstring(targetItem.name).chain((substring) =>
            // Generate some additional random items
            fc
              .array(arbitraryPickerItem(), { minLength: 0, maxLength: 5 })
              .map((otherItems) => ({
                targetItem,
                substring,
                allItems: [targetItem, ...otherItems],
              }))
          )
        ),
        ({ targetItem, substring, allItems }) => {
          const results = smartSearch(allItems, substring, {});
          const resultNames = results.map((r) => r.name);

          expect(resultNames).toContain(targetItem.name);
        }
      ),
      { numRuns: 100 }
    );
  });
});
