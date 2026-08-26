import { render, screen, fireEvent } from '@testing-library/react';
import { ABBREVIATION_MAP } from '@/data/abbreviation-map';
import { smartSearch } from '@/utils/object-search';
import type { PickerItem } from '@/data/object-catalog';
import ObjectSidebar from '@/components/objects/ObjectSidebar';
import { useDiagramStore } from '@/store/diagram-store';
import { useLayoutPreferencesStore } from '@/store/layout-preferences-store';
import { usePinnedObjectsStore } from '@/store/pinned-objects-store';
import { useRecentlyUsedStore } from '@/store/recently-used-store';

// Requirements: 2.2, 2.5, 3.6, 1.4, 1.6

function makeItem(name: string, category = 'Shapes'): PickerItem {
  return { name, category, tool: 'pointer' };
}

describe('ObjectSidebar', () => {
  beforeEach(() => {
    useRecentlyUsedStore.getState().clearRecentItems();
    usePinnedObjectsStore.getState().clearPins();
    useLayoutPreferencesStore.getState().setObjectSidebarCollapsed(false);
    useLayoutPreferencesStore.getState().setObjectSidebarPosition('left');
    useLayoutPreferencesStore.getState().setObjectSidebarWidth(240);
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
    const items: PickerItem[] = [makeItem('Rectangle'), makeItem('Circle'), makeItem('Lambda')];
    expect(smartSearch(items, 'xyzzyplugh999', ABBREVIATION_MAP)).toHaveLength(0);
  });

  test('renders the shortlist and the catalog without needing to be opened', () => {
    render(<ObjectSidebar />);
    expect(screen.getByTestId('object-sidebar')).toBeTruthy();
    expect(screen.getByTestId('object-sidebar-search')).toBeTruthy();
    expect(screen.getByTestId('object-shortlist')).toBeTruthy();
    expect(screen.getByTestId('picker-category-Shapes')).toBeTruthy();
  });

  test('categories stay collapsed until opened', () => {
    render(<ObjectSidebar />);
    expect(screen.queryByTestId('picker-item-Rectangle')).toBeNull();
    fireEvent.click(screen.getByTestId('picker-category-toggle-Shapes'));
    expect(screen.getByTestId('picker-item-Rectangle')).toBeTruthy();
  });

  test('search hides the categories that have no match and counts the rest', () => {
    render(<ObjectSidebar />);

    fireEvent.change(screen.getByTestId('object-sidebar-search'), {
      target: { value: 'rectangle' },
    });

    expect(screen.getByTestId('picker-category-Shapes')).toBeTruthy();
    expect(screen.queryByTestId('picker-category-UML')).toBeNull();
    expect(screen.getByTestId('object-search-count').textContent).toBe('2 matches');
  });

  test('searching replaces the shortlist with results', () => {
    render(<ObjectSidebar />);
    expect(screen.getByTestId('object-shortlist')).toBeTruthy();

    fireEvent.change(screen.getByTestId('object-sidebar-search'), { target: { value: 'lambda' } });

    expect(screen.queryByTestId('object-shortlist')).toBeNull();
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
  });

  test('the armed bar names what is being placed and cancels it', () => {
    render(<ObjectSidebar />);
    expect(screen.queryByTestId('object-armed-bar')).toBeNull();

    fireEvent.click(screen.getByTestId('picker-category-toggle-Shapes'));
    fireEvent.click(screen.getByTestId('picker-item-Rectangle'));

    expect(screen.getByTestId('object-armed-bar').textContent).toContain('Placing Rectangle');

    fireEvent.click(screen.getByTestId('object-armed-cancel'));

    expect(useDiagramStore.getState().activeTool).toBe('pointer');
    expect(screen.queryByTestId('object-armed-bar')).toBeNull();
  });

  test('pinning keeps an object at the top without arming it', () => {
    render(<ObjectSidebar />);

    fireEvent.click(screen.getByTestId('picker-category-toggle-Shapes'));
    fireEvent.click(screen.getByTestId('picker-pin-Rectangle'));

    expect(usePinnedObjectsStore.getState().pinnedItems.map((p) => p.name)).toEqual(['Rectangle']);
    expect(useDiagramStore.getState().activeTool).toBe('pointer');
    // Once pinned it appears in the shortlist as well as in its category
    expect(screen.getAllByTestId('picker-item-Rectangle').length).toBe(2);
  });

  test('recent objects use full-size tiles and can be pinned', () => {
    useRecentlyUsedStore.getState().addRecentItem(makeItem('Rectangle'));
    render(<ObjectSidebar />);

    fireEvent.click(screen.getByTestId('picker-pin-Rectangle'));

    expect(usePinnedObjectsStore.getState().pinnedItems.map((p) => p.name)).toEqual(['Rectangle']);
  });

  test('resizing persists the sidebar width', () => {
    render(<ObjectSidebar />);

    fireEvent.pointerDown(screen.getByTestId('object-sidebar-resize-handle'), { clientX: 240 });
    fireEvent.pointerMove(window, { clientX: 300 });
    fireEvent.pointerUp(window);

    expect(useLayoutPreferencesStore.getState().objectSidebarWidth).toBe(300);
    expect(screen.getByTestId('object-sidebar').style.width).toBe('300px');
  });

  test('can move the sidebar to the right', () => {
    useLayoutPreferencesStore.getState().setObjectSidebarPosition('right');
    render(<ObjectSidebar />);

    expect(screen.getByTestId('object-sidebar').getAttribute('data-position')).toBe('right');
    expect(screen.getByTestId('object-sidebar').className).toContain('order-2');
  });

  test('an AWS service without a generator cannot be placed or pinned', () => {
    render(<ObjectSidebar />);
    fireEvent.change(screen.getByTestId('object-sidebar-search'), { target: { value: 'AppFlow' } });

    expect((screen.getByTestId('picker-item-AppFlow') as HTMLButtonElement).disabled).toBe(true);
    expect(screen.queryByTestId('picker-pin-AppFlow')).toBeNull();
  });

  test('collapsing hides the catalog and persists the preference', () => {
    render(<ObjectSidebar />);

    fireEvent.click(screen.getByTestId('object-sidebar-toggle'));

    expect(useLayoutPreferencesStore.getState().objectSidebarCollapsed).toBe(true);
    expect(screen.getByTestId('object-sidebar').getAttribute('data-collapsed')).toBe('true');
    expect(screen.queryByTestId('object-sidebar-search')).toBeNull();
    expect(screen.queryByTestId('picker-category-Shapes')).toBeNull();
  });

  test('the rail keeps pinned objects reachable', () => {
    usePinnedObjectsStore.getState().togglePin(makeItem('Rectangle'));
    useLayoutPreferencesStore.getState().setObjectSidebarCollapsed(true);
    render(<ObjectSidebar />);

    expect(screen.getByTestId('object-sidebar').getAttribute('data-collapsed')).toBe('true');
    expect(screen.getByTestId('picker-item-Rectangle')).toBeTruthy();
    expect(screen.getByTestId('object-sidebar-search-open')).toBeTruthy();
  });
});
