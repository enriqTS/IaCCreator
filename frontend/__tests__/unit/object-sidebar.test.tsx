import { render, screen, fireEvent } from '@testing-library/react';
import { ABBREVIATION_MAP } from '@/data/abbreviation-map';
import { smartSearch } from '@/utils/object-search';
import type { PickerItem } from '@/data/object-catalog';
import ObjectSidebar from '@/components/objects/ObjectSidebar';
import { useDiagramStore } from '@/store/diagram-store';
import { useLayoutPreferencesStore } from '@/store/layout-preferences-store';
import { useRecentlyUsedStore } from '@/store/recently-used-store';

// Requirements: 2.2, 2.5, 3.6, 1.4, 1.6

function makeItem(name: string, category = 'Shapes'): PickerItem {
  return { name, category, tool: 'pointer' };
}

describe('ObjectSidebar', () => {
  beforeEach(() => {
    useRecentlyUsedStore.getState().clearRecentItems();
    useLayoutPreferencesStore.getState().setObjectSidebarCollapsed(false);
    useDiagramStore.getState().setActiveTool('pointer');
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

  test('renders without needing to be opened', () => {
    render(<ObjectSidebar />);
    expect(screen.getByTestId('object-sidebar')).toBeTruthy();
    expect(screen.getByTestId('object-sidebar-search')).toBeTruthy();
    expect(screen.getByTestId('picker-category-Shapes')).toBeTruthy();
  });

  test('Recently Used group hidden when empty', () => {
    render(<ObjectSidebar />);
    expect(screen.queryByTestId('picker-category-Recently Used')).toBeNull();
  });

  test('search hides the categories that have no match', () => {
    render(<ObjectSidebar />);

    fireEvent.change(screen.getByTestId('object-sidebar-search'), {
      target: { value: 'rectangle' },
    });

    expect(screen.getByTestId('picker-category-Shapes')).toBeTruthy();
    expect(screen.queryByTestId('picker-category-UML')).toBeNull();
  });

  test('a nonsense search term reports no items', () => {
    render(<ObjectSidebar />);

    fireEvent.change(screen.getByTestId('object-sidebar-search'), {
      target: { value: 'xyzzyplugh999' },
    });

    expect(screen.getByText('No items found')).toBeTruthy();
  });

  test('selecting an item arms its tool and leaves the sidebar open', () => {
    render(<ObjectSidebar />);

    fireEvent.click(screen.getByTestId('picker-category-toggle-Shapes'));
    fireEvent.click(screen.getByTestId('picker-item-Rectangle'));

    expect(useDiagramStore.getState().activeTool).toEqual({
      type: 'place-shape',
      shape: 'rectangle',
    });
    expect(screen.getByTestId('object-sidebar')).toBeTruthy();
    // It now also appears under Recently Used, and both copies show as armed
    for (const tile of screen.getAllByTestId('picker-item-Rectangle')) {
      expect(tile.getAttribute('aria-pressed')).toBe('true');
    }
  });

  test('an AWS service without a generator cannot be placed', () => {
    render(<ObjectSidebar />);

    fireEvent.change(screen.getByTestId('object-sidebar-search'), {
      target: { value: 'AppFlow' },
    });

    const item = screen.getByTestId('picker-item-AppFlow') as HTMLButtonElement;
    expect(item.disabled).toBe(true);
  });

  test('collapsing hides the catalog and persists the preference', () => {
    render(<ObjectSidebar />);

    fireEvent.click(screen.getByTestId('object-sidebar-toggle'));

    expect(useLayoutPreferencesStore.getState().objectSidebarCollapsed).toBe(true);
    expect(screen.getByTestId('object-sidebar').getAttribute('data-collapsed')).toBe('true');
    expect(screen.queryByTestId('object-sidebar-search')).toBeNull();
    expect(screen.queryByTestId('picker-category-Shapes')).toBeNull();
  });
});
