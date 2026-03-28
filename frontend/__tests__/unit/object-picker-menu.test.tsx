import { render, screen, fireEvent } from '@testing-library/react';
import { ABBREVIATION_MAP } from '@/data/abbreviation-map';
import { smartSearch } from '@/components/toolbar/ObjectPickerMenu';
import type { PickerItem } from '@/components/toolbar/ObjectPickerMenu';
import ObjectPickerMenu from '@/components/toolbar/ObjectPickerMenu';
import { useRecentlyUsedStore } from '@/store/recently-used-store';
import { useDiagramStore } from '@/store/diagram-store';

// Requirements: 2.2, 2.5, 3.6, 1.4, 1.6

function makeItem(name: string, category = 'Shapes'): PickerItem {
  return { name, category, tool: 'pointer' };
}

describe('ObjectPickerMenu edge cases', () => {
  beforeEach(() => {
    useRecentlyUsedStore.getState().clearRecentItems();
  });

  test('abbreviation map contains all required keys', () => {
    const requiredKeys = ['s3', 'ec2', 'ecs', 'eks', 'rds', 'sns', 'sqs', 'iam', 'cfn'];
    for (const key of requiredKeys) {
      expect(ABBREVIATION_MAP).toHaveProperty(key);
      expect(Array.isArray(ABBREVIATION_MAP[key])).toBe(true);
      expect(ABBREVIATION_MAP[key].length).toBeGreaterThan(0);
    }
  });

  test('"No items found" message for nonsense search term', () => {
    const items: PickerItem[] = [
      makeItem('Rectangle'),
      makeItem('Circle'),
      makeItem('Lambda'),
    ];
    const results = smartSearch(items, 'xyzzyplugh999', ABBREVIATION_MAP);
    expect(results).toHaveLength(0);
  });

  test('Recently Used group hidden when empty', () => {
    render(<ObjectPickerMenu />);

    // Open the picker
    const button = screen.getByTestId('object-picker-button');
    fireEvent.click(button);

    // The dropdown should be open
    expect(screen.getByTestId('object-picker-dropdown')).toBeTruthy();

    // "Recently Used" category should NOT be present when no recent items
    expect(screen.queryByTestId('picker-category-Recently Used')).toBeNull();
  });

  test('panel closes after item selection', () => {
    render(<ObjectPickerMenu />);

    // Open the picker
    const button = screen.getByTestId('object-picker-button');
    fireEvent.click(button);

    // The dropdown should be open
    expect(screen.getByTestId('object-picker-dropdown')).toBeTruthy();

    // Click the first available picker item
    const firstItem = screen.getAllByTestId(/^picker-item-/)[0];
    fireEvent.click(firstItem);

    // The dropdown should be closed
    expect(screen.queryByTestId('object-picker-dropdown')).toBeNull();
  });
});
