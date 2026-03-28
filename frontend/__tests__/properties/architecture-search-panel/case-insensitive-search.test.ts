import fc from 'fast-check';
import { smartSearch } from '@/components/toolbar/ObjectPickerMenu';
import type { PickerItem } from '@/components/toolbar/ObjectPickerMenu';
import { ABBREVIATION_MAP } from '@/data/abbreviation-map';

// Feature: architecture-search-panel, Property 3: Case-insensitive search equivalence
// **Validates: Requirements 2.4**

/**
 * Helper to create a PickerItem with a given name.
 */
function pickerItemWithName(name: string): PickerItem {
  return {
    name,
    category: 'Shapes',
    tool: 'pointer',
  };
}

/**
 * Arbitrary that generates a random PickerItem with a non-empty, trimmed name.
 */
function arbitraryPickerItem(): fc.Arbitrary<PickerItem> {
  return fc
    .string({ minLength: 1, maxLength: 40 })
    .filter((s) => s.trim().length > 0)
    .map((name) => pickerItemWithName(name));
}

/**
 * Given a string, produce a random casing variation by independently
 * upper- or lower-casing each character.
 */
function arbitraryCasingVariation(term: string): fc.Arbitrary<string> {
  return fc
    .array(fc.boolean(), { minLength: term.length, maxLength: term.length })
    .map((flags) =>
      term
        .split('')
        .map((ch, i) => (flags[i] ? ch.toUpperCase() : ch.toLowerCase()))
        .join('')
    );
}

describe('Property 3: Case-insensitive search equivalence', () => {
  test('smartSearch returns the same set of items regardless of search term casing', () => {
    fc.assert(
      fc.property(
        // Generate a list of items and a non-empty search term, then two casing variations
        fc.array(arbitraryPickerItem(), { minLength: 1, maxLength: 10 }).chain((items) =>
          fc
            .string({ minLength: 1, maxLength: 20 })
            .filter((s) => s.trim().length > 0)
            .chain((baseTerm) =>
              fc
                .tuple(
                  arbitraryCasingVariation(baseTerm),
                  arbitraryCasingVariation(baseTerm)
                )
                .map(([casingA, casingB]) => ({
                  items,
                  casingA,
                  casingB,
                }))
            )
        ),
        ({ items, casingA, casingB }) => {
          const resultsA = smartSearch(items, casingA, ABBREVIATION_MAP);
          const resultsB = smartSearch(items, casingB, ABBREVIATION_MAP);

          const namesA = resultsA.map((r) => r.name).sort();
          const namesB = resultsB.map((r) => r.name).sort();

          expect(namesA).toEqual(namesB);
        }
      ),
      { numRuns: 100 }
    );
  });
});
