import type { PickerCategory, PickerItem } from '@/data/object-catalog';

// Matches on a case-insensitive substring, and also on the full names an abbreviation expands to
export function smartSearch(
  items: PickerItem[],
  searchTerm: string,
  abbreviationMap: Record<string, string[]>
): PickerItem[] {
  if (!searchTerm || searchTerm.trim() === '') return items;

  const lower = searchTerm.toLowerCase();

  // Object.hasOwn keeps prototype keys like "constructor" from matching
  const expandedNames = Object.hasOwn(abbreviationMap, lower) ? abbreviationMap[lower] : undefined;
  const lowerExpandedNames = expandedNames
    ? expandedNames.map((n) => n.toLowerCase())
    : [];

  return items.filter((item) => {
    const itemNameLower = item.name.toLowerCase();

    if (itemNameLower.includes(lower)) return true;

    if (lowerExpandedNames.length > 0) {
      return lowerExpandedNames.some((expanded) => itemNameLower.includes(expanded));
    }

    return false;
  });
}

// Fixed categories lead in a curated order, AWS categories follow alphabetically
export function sortCategories(categories: PickerCategory[]): PickerCategory[] {
  const fixedOrder: Record<string, number> = {
    'Recently Used': 0,
    'Shapes': 1,
    'UML': 2,
    'Text': 3,
    'Lines & Arrows': 4,
  };

  return [...categories].sort((a, b) => {
    const aFixed = fixedOrder[a.category];
    const bFixed = fixedOrder[b.category];

    if (aFixed !== undefined && bFixed !== undefined) {
      return aFixed - bFixed;
    }

    if (aFixed !== undefined) return -1;

    if (bFixed !== undefined) return 1;

    return a.category.localeCompare(b.category);
  });
}
