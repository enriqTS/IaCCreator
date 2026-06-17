'use client';

import { useState, useRef, useEffect } from 'react';
import { AWS_ICON_REGISTRY } from '@/data/aws-icon-registry';
import { ABBREVIATION_MAP } from '@/data/abbreviation-map';
import { useDiagramStore } from '@/store/diagram-store';
import { useRecentlyUsedStore } from '@/store/recently-used-store';
import { getItemIcon } from '@/data/shape-icons';
import type { GeometricShape, UMLKind, Tool } from '@/types/diagram';

// --- Picker item types ---

export interface PickerItem {
  name: string;
  category: string;
  icon?: string; // SVG path or icon URL
  tool: Tool;
}

// --- Static registries ---

const GEOMETRIC_SHAPES: { name: string; shape: GeometricShape }[] = [
  { name: 'Rectangle', shape: 'rectangle' },
  { name: 'Rounded Rectangle', shape: 'rounded-rectangle' },
  { name: 'Ellipse', shape: 'ellipse' },
  { name: 'Circle', shape: 'circle' },
  { name: 'Triangle', shape: 'triangle' },
  { name: 'Diamond', shape: 'diamond' },
  { name: 'Parallelogram', shape: 'parallelogram' },
  { name: 'Trapezoid', shape: 'trapezoid' },
  { name: 'Hexagon', shape: 'hexagon' },
  { name: 'Octagon', shape: 'octagon' },
  { name: 'Pentagon', shape: 'pentagon' },
  { name: 'Star', shape: 'star' },
  { name: 'Cross', shape: 'cross' },
  { name: 'Arrow Right', shape: 'arrow-right' },
  { name: 'Arrow Left', shape: 'arrow-left' },
  { name: 'Arrow Up', shape: 'arrow-up' },
  { name: 'Arrow Down', shape: 'arrow-down' },
  { name: 'Chevron', shape: 'chevron' },
  { name: 'Cylinder', shape: 'cylinder' },
  { name: 'Cloud', shape: 'cloud' },
  { name: 'Callout', shape: 'callout' },
  { name: 'Document', shape: 'document' },
  { name: 'Process', shape: 'process' },
  { name: 'Decision', shape: 'decision' },
  { name: 'Data', shape: 'data' },
  { name: 'Predefined Process', shape: 'predefined-process' },
];

const UML_ELEMENTS: { name: string; kind: UMLKind }[] = [
  { name: 'Class', kind: 'class' },
  { name: 'Interface', kind: 'interface' },
  { name: 'Actor', kind: 'actor' },
  { name: 'Use Case', kind: 'use-case' },
  { name: 'Component', kind: 'component' },
  { name: 'Package', kind: 'package' },
  { name: 'Node', kind: 'node' },
];

// --- Build all picker items ---

function buildAllPickerItems(): { category: string; items: PickerItem[] }[] {
  const categories: { category: string; items: PickerItem[] }[] = [];

  // AWS Services
  for (const cat of AWS_ICON_REGISTRY) {
    const items: PickerItem[] = cat.services.map((svc) => ({
      name: svc.name,
      category: `AWS: ${cat.name}`,
      icon: svc.iconPath,
      tool: svc.serviceType
        ? ({ type: 'place-service', serviceType: svc.serviceType } as Tool)
        : ('pointer' as Tool), // unsupported services default to pointer (disabled)
    }));
    categories.push({ category: `AWS: ${cat.name}`, items });
  }

  // Shapes
  categories.push({
    category: 'Shapes',
    items: GEOMETRIC_SHAPES.map((s) => ({
      name: s.name,
      category: 'Shapes',
      tool: { type: 'place-shape', shape: s.shape } as Tool,
    })),
  });

  // UML
  categories.push({
    category: 'UML',
    items: UML_ELEMENTS.map((u) => ({
      name: u.name,
      category: 'UML',
      tool: { type: 'place-uml', umlKind: u.kind } as Tool,
    })),
  });

  // Text
  categories.push({
    category: 'Text',
    items: [{ name: 'Text', category: 'Text', tool: 'text' as Tool }],
  });

  // Lines & Arrows
  categories.push({
    category: 'Lines & Arrows',
    items: [
      { name: 'Line', category: 'Lines & Arrows', tool: 'line' as Tool },
      { name: 'Arrow', category: 'Lines & Arrows', tool: 'connector' as Tool },
    ],
  });

  return categories;
}

const ALL_CATEGORIES = buildAllPickerItems();

// Flat list for search
const ALL_ITEMS: PickerItem[] = ALL_CATEGORIES.flatMap((c) => c.items);

/**
 * Filter picker items by search term (case-insensitive name match).
 * Exported for testing (Property 10).
 * @deprecated Use smartSearch() instead, which adds abbreviation-aware matching.
 */
export function filterPickerItems(items: PickerItem[], searchTerm: string): PickerItem[] {
  if (!searchTerm || searchTerm.trim() === '') return items;
  const lower = searchTerm.toLowerCase();
  return items.filter((item) => item.name.toLowerCase().includes(lower));
}

/**
 * Smart search: matches items by case-insensitive substring on name,
 * and also expands abbreviation map keys to their full service names.
 *
 * Matching logic:
 * 1. Empty/whitespace search term → return all items
 * 2. Lowercase the term
 * 3. If the term is a key in abbreviationMap, collect expanded full names
 * 4. An item matches if:
 *    - item.name contains the search term as a substring (case-insensitive), OR
 *    - item.name matches any expanded abbreviation name (case-insensitive)
 * 5. All matching is case-insensitive
 */
export function smartSearch(
  items: PickerItem[],
  searchTerm: string,
  abbreviationMap: Record<string, string[]>
): PickerItem[] {
  if (!searchTerm || searchTerm.trim() === '') return items;

  const lower = searchTerm.toLowerCase();

  // Look up expanded names from the abbreviation map
  // Use Object.hasOwn to avoid matching Object.prototype properties (e.g., "constructor", "toString")
  const expandedNames = Object.hasOwn(abbreviationMap, lower) ? abbreviationMap[lower] : undefined;
  const lowerExpandedNames = expandedNames
    ? expandedNames.map((n) => n.toLowerCase())
    : [];

  return items.filter((item) => {
    const itemNameLower = item.name.toLowerCase();

    // Substring match on the search term
    if (itemNameLower.includes(lower)) return true;

    // Match against any expanded abbreviation name
    if (lowerExpandedNames.length > 0) {
      return lowerExpandedNames.some((expanded) => itemNameLower.includes(expanded));
    }

    return false;
  });
}

/**
 * Sort categories in the defined display order:
 * 1. "Recently Used" always first
 * 2. "Shapes" second
 * 3. "UML" third
 * 4. "Text" fourth
 * 5. "Lines & Arrows" fifth
 * 6. All AWS categories (starting with "AWS:") in alphabetical order
 *
 * Returns a new sorted array without mutating the input.
 */
export function sortCategories(
  categories: { category: string; items: PickerItem[] }[]
): { category: string; items: PickerItem[] }[] {
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

    // Both have fixed positions
    if (aFixed !== undefined && bFixed !== undefined) {
      return aFixed - bFixed;
    }

    // Only a has a fixed position → a comes first
    if (aFixed !== undefined) return -1;

    // Only b has a fixed position → b comes first
    if (bFixed !== undefined) return 1;

    // Neither has a fixed position → alphabetical (AWS categories)
    return a.category.localeCompare(b.category);
  });
}

export default function ObjectPickerMenu() {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(new Set());
  const setActiveTool = useDiagramStore((s) => s.setActiveTool);
  const recentItems = useRecentlyUsedStore((s) => s.recentItems);
  const addRecentItem = useRecentlyUsedStore((s) => s.addRecentItem);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  const filteredItems = smartSearch(ALL_ITEMS, search, ABBREVIATION_MAP);
  const filteredItemNames = new Set(filteredItems.map((i) => i.name + '|' + i.category));

  const toggleCategory = (name: string) => {
    setCollapsedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  // Filter categories to only show those with matching items
  const baseCategories = ALL_CATEGORIES.map((cat) => ({
    ...cat,
    items: cat.items.filter((item) => filteredItemNames.has(item.name + '|' + item.category)),
  })).filter((cat) => cat.items.length > 0);

  // Build Recently Used category (only when non-empty)
  const recentlyUsedCategory: { category: string; items: PickerItem[] }[] =
    recentItems.length > 0
      ? [{ category: 'Recently Used', items: recentItems }]
      : [];

  // Prepend Recently Used and apply sort ordering
  const visibleCategories = sortCategories([...recentlyUsedCategory, ...baseCategories]);

  const isAWSService = (item: PickerItem) =>
    typeof item.tool === 'object' && 'type' in item.tool && item.tool.type === 'place-service';

  const isUnsupportedAWS = (item: PickerItem) =>
    item.category.startsWith('AWS:') && !isAWSService(item);

  return (
    <div ref={containerRef} style={{ position: 'relative' }}>
      <button
        data-testid="object-picker-button"
        title="Add Object"
        onClick={() => { setOpen((v) => !v); setSearch(''); }}
        style={{
          width: 36,
          height: 36,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: 8,
          border: 'none',
          cursor: 'pointer',
          fontSize: 20,
          fontWeight: 'bold',
          background: open ? 'rgba(59, 130, 246, 0.3)' : 'transparent',
          color: '#e5e5e5',
          transition: 'background 0.15s',
        }}
        onMouseEnter={(e) => {
          if (!open) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = open ? 'rgba(59, 130, 246, 0.3)' : 'transparent';
        }}
      >
        +
      </button>

      {open && (
        <div
          data-testid="object-picker-dropdown"
          style={{
            position: 'absolute',
            top: 44,
            left: '50%',
            transform: 'translateX(-50%)',
            width: 420,
            maxHeight: 420,
            overflowY: 'auto',
            background: '#1e1e1e',
            borderRadius: 10,
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.6)',
            border: '1px solid #333',
            zIndex: 100,
            padding: '8px 0',
          }}
        >
          {/* Search input */}
          <div style={{ padding: '4px 8px 8px' }}>
            <input
              data-testid="object-picker-search"
              type="text"
              placeholder="Search objects..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              autoFocus
              style={{
                width: '100%',
                padding: '6px 10px',
                borderRadius: 6,
                border: '1px solid #444',
                background: '#2a2a2a',
                color: '#e5e5e5',
                fontSize: 13,
                outline: 'none',
                boxSizing: 'border-box',
              }}
            />
          </div>

          {visibleCategories.length === 0 && (
            <div style={{ padding: '12px 16px', color: '#888', fontSize: 13 }}>
              No items found
            </div>
          )}

          {visibleCategories.map((cat) => {
            const isCollapsed = collapsedCategories.has(cat.category);
            return (
              <div key={cat.category} data-testid={`picker-category-${cat.category}`}>
                <button
                  data-testid={`picker-category-toggle-${cat.category}`}
                  onClick={() => toggleCategory(cat.category)}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: '6px 12px',
                    background: 'transparent',
                    border: 'none',
                    color: '#aaa',
                    fontSize: 11,
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                >
                  <span style={{ fontSize: 9 }}>{isCollapsed ? '▶' : '▼'}</span>
                  {cat.category}
                </button>

                {!isCollapsed && (
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fill, minmax(72px, 1fr))',
                      gap: 4,
                      padding: '4px 8px',
                    }}
                  >
                    {cat.items.map((item) => {
                      const disabled = isUnsupportedAWS(item);
                      return (
                        <button
                          key={`${item.category}-${item.name}`}
                          data-testid={`picker-item-${item.name}`}
                          title={item.name}
                          disabled={disabled}
                          onClick={() => {
                            if (!disabled) {
                              addRecentItem(item);
                              setActiveTool(item.tool);
                              setOpen(false);
                            }
                          }}
                          style={{
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: 2,
                            background: 'transparent',
                            border: 'none',
                            borderRadius: 6,
                            cursor: disabled ? 'default' : 'pointer',
                            opacity: disabled ? 0.4 : 1,
                            padding: '4px 2px',
                            minWidth: 0,
                          }}
                          onMouseEnter={(e) => {
                            if (!disabled) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)';
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.background = 'transparent';
                          }}
                        >
                          <div style={{ width: 28, height: 28, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                            {item.icon ? (
                              // eslint-disable-next-line @next/next/no-img-element
                              <img src={item.icon} alt={item.name} width={28} height={28} />
                            ) : (
                              getItemIcon(item.name) || (
                                <span
                                  style={{
                                    color: '#e5e5e5',
                                    fontSize: 12,
                                    fontWeight: 600,
                                    lineHeight: 1,
                                    userSelect: 'none',
                                  }}
                                >
                                  {item.name.slice(0, 2)}
                                </span>
                              )
                            )}
                          </div>
                          <span
                            style={{
                              fontSize: 9,
                              color: '#ccc',
                              lineHeight: 1.2,
                              width: '100%',
                              textAlign: 'center',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {item.name}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
