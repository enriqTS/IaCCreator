import fc from 'fast-check';
import { ABBREVIATION_MAP } from '@/data/abbreviation-map';
import { smartSearch } from '@/components/toolbar/ObjectPickerMenu';
import type { PickerItem } from '@/components/toolbar/ObjectPickerMenu';

// Feature: architecture-search-panel, Property 2: Abbreviation search expansion
// **Validates: Requirements 2.1**

/**
 * Arbitrary that generates a PickerItem with a given name.
 */
function pickerItemWithName(name: string): fc.Arbitrary<PickerItem> {
  return fc.record({
    name: fc.constant(name),
    category: fc.constantFrom('AWS: Compute', 'AWS: Storage', 'AWS: Database', 'Shapes', 'UML'),
    icon: fc.option(fc.constant('/icons/test.svg'), { nil: undefined }),
    tool: fc.constant('pointer' as PickerItem['tool']),
  });
}

/**
 * Arbitrary that generates a PickerItem with a random name that does NOT match
 * any of the provided full names and does NOT contain the abbreviation key as a substring.
 */
function nonMatchingPickerItem(fullNames: string[], abbrevKey: string): fc.Arbitrary<PickerItem> {
  const lowerFullNames = fullNames.map((n) => n.toLowerCase());
  const lowerKey = abbrevKey.toLowerCase();

  return fc
    .string({ minLength: 1, maxLength: 30 })
    .filter((name) => {
      const lowerName = name.toLowerCase();
      // Must not match any expanded full name (as substring in the item name)
      const matchesFullName = lowerFullNames.some((fn) => lowerName.includes(fn));
      // Must not contain the abbreviation key as substring
      const containsKey = lowerName.includes(lowerKey);
      return !matchesFullName && !containsKey;
    })
    .map((name) => ({
      name,
      category: 'AWS: Other',
      tool: 'pointer' as PickerItem['tool'],
    }));
}

const abbreviationKeys = Object.keys(ABBREVIATION_MAP);

describe('Property 2: Abbreviation search expansion', () => {
  test('smartSearch with an abbreviation key returns every item matching an expanded name and excludes non-matching items', () => {
    fc.assert(
      fc.property(
        // Pick a random key from the abbreviation map
        fc.constantFrom(...abbreviationKeys).chain((abbrevKey) => {
          const fullNames = ABBREVIATION_MAP[abbrevKey];

          // Generate matching items: one for each expanded full name
          const matchingItemsArb = fc.tuple(
            ...fullNames.map((fullName) => pickerItemWithName(fullName))
          );

          // Generate some non-matching items
          const nonMatchingItemsArb = fc.array(
            nonMatchingPickerItem(fullNames, abbrevKey),
            { minLength: 0, maxLength: 5 }
          );

          return fc.tuple(
            fc.constant(abbrevKey),
            fc.constant(fullNames),
            matchingItemsArb,
            nonMatchingItemsArb
          );
        }),
        ([abbrevKey, fullNames, matchingItems, nonMatchingItems]) => {
          const allItems: PickerItem[] = [...matchingItems, ...nonMatchingItems];

          const results = smartSearch(allItems, abbrevKey, ABBREVIATION_MAP);
          const resultNames = results.map((r) => r.name);

          // Every matching item (whose name is an expanded full name) must be in results
          for (const item of matchingItems) {
            expect(resultNames).toContain(item.name);
          }

          // Non-matching items (name doesn't match any expanded name AND doesn't contain key)
          // must NOT be in results
          for (const item of nonMatchingItems) {
            expect(resultNames).not.toContain(item.name);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
