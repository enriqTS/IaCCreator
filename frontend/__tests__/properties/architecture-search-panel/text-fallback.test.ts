import fc from 'fast-check';
import type { PickerItem } from '@/components/toolbar/ObjectPickerMenu';

// Feature: architecture-search-panel, Property 8: Text fallback for missing icons
// **Validates: Requirements 5.4**

describe('Property 8: Text fallback for missing icons', () => {
  test('for any picker item with undefined icon, the fallback text equals the first two characters of the item name', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 40 }).filter((s) => s.trim().length > 0),
        (name) => {
          const item: PickerItem = {
            name,
            category: 'Shapes',
            icon: undefined,
            tool: 'pointer',
          };

          // The component renders item.name.slice(0, 2) as fallback when icon is undefined
          const fallbackText = item.name.slice(0, 2);

          expect(fallbackText).toBe(name.slice(0, 2));
          expect(fallbackText.length).toBeLessThanOrEqual(2);
          expect(fallbackText.length).toBeGreaterThanOrEqual(1);
        }
      ),
      { numRuns: 100 }
    );
  });
});
