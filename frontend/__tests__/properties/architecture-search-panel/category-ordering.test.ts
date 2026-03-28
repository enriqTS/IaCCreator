import fc from 'fast-check';
import { sortCategories } from '@/components/toolbar/ObjectPickerMenu';
import type { PickerItem } from '@/components/toolbar/ObjectPickerMenu';

// Feature: architecture-search-panel, Property 7: Category ordering invariant
// **Validates: Requirements 4.1, 4.2, 4.3, 2.3**

/**
 * Fixed (non-AWS) categories in their required order.
 */
const FIXED_CATEGORIES = ['Recently Used', 'Shapes', 'UML', 'Text', 'Lines & Arrows'];

/**
 * Example AWS categories for generating test data.
 */
const AWS_CATEGORIES = [
  'AWS: Analytics',
  'AWS: Application Integration',
  'AWS: Compute',
  'AWS: Database',
  'AWS: Developer Tools',
  'AWS: Machine Learning',
  'AWS: Management & Governance',
  'AWS: Networking & Content Delivery',
  'AWS: Security, Identity, & Compliance',
  'AWS: Storage',
];

/**
 * All possible categories to pick from.
 */
const ALL_CATEGORIES = [...FIXED_CATEGORIES, ...AWS_CATEGORIES];

/**
 * Create a dummy category group entry with a placeholder item.
 */
function makeCategoryGroup(category: string): { category: string; items: PickerItem[] } {
  return {
    category,
    items: [{ name: `${category} Item`, category, tool: 'pointer' }],
  };
}

describe('Property 7: Category ordering invariant', () => {
  test('sortCategories places fixed categories before AWS categories in the correct order, with AWS categories alphabetical', () => {
    fc.assert(
      fc.property(
        // Generate a random non-empty subset of all categories
        fc
          .subarray(ALL_CATEGORIES, { minLength: 1 })
          .map((cats) => cats.map(makeCategoryGroup)),
        (categories) => {
          const sorted = sortCategories(categories);
          const sortedNames = sorted.map((c) => c.category);

          // 1. Extract the fixed categories that appear in the sorted result
          const fixedInResult = sortedNames.filter((c) => FIXED_CATEGORIES.includes(c));
          // They must appear in the same relative order as FIXED_CATEGORIES
          const expectedFixedOrder = FIXED_CATEGORIES.filter((c) => fixedInResult.includes(c));
          expect(fixedInResult).toEqual(expectedFixedOrder);

          // 2. Extract the AWS categories that appear in the sorted result
          const awsInResult = sortedNames.filter((c) => c.startsWith('AWS:'));
          // AWS categories must be in alphabetical order
          const awsSorted = [...awsInResult].sort((a, b) => a.localeCompare(b));
          expect(awsInResult).toEqual(awsSorted);

          // 3. All fixed categories must come before all AWS categories
          if (fixedInResult.length > 0 && awsInResult.length > 0) {
            const lastFixedIndex = sortedNames.lastIndexOf(fixedInResult[fixedInResult.length - 1]);
            const firstAwsIndex = sortedNames.indexOf(awsInResult[0]);
            expect(lastFixedIndex).toBeLessThan(firstAwsIndex);
          }

          // 4. No items lost — same set of categories in output as input
          const inputNames = categories.map((c) => c.category).sort();
          const outputNames = [...sortedNames].sort();
          expect(outputNames).toEqual(inputNames);
        }
      ),
      { numRuns: 100 }
    );
  });
});
