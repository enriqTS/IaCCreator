'use client';

import { useState, useRef, useEffect } from 'react';
import { ABBREVIATION_MAP } from '@/data/abbreviation-map';
import { useDiagramStore } from '@/store/diagram-store';
import { useRecentlyUsedStore } from '@/store/recently-used-store';
import { getItemIcon } from '@/data/shape-icons';
import {
  ALL_CATEGORIES,
  ALL_CATEGORY_NAMES,
  ALL_ITEMS,
  isUnsupportedAwsItem,
  type PickerCategory,
} from '@/data/object-catalog';
import { smartSearch, sortCategories } from '@/utils/object-search';

export default function ObjectPickerMenu() {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  // Start with all categories collapsed for performance - SVGs load only when expanded
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(new Set(ALL_CATEGORY_NAMES));
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

  // Auto-expand categories that have matching items when searching
  const categoriesWithMatches = new Set(
    filteredItems.map((item) => item.category)
  );

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
  const recentlyUsedCategory: PickerCategory[] =
    recentItems.length > 0
      ? [{ category: 'Recently Used', items: recentItems }]
      : [];

  // Prepend Recently Used and apply sort ordering
  const visibleCategories = sortCategories([...recentlyUsedCategory, ...baseCategories]);

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
            // Auto-expand when searching and category has matches
            const isCollapsed = search.trim() !== '' && categoriesWithMatches.has(cat.category)
              ? false
              : collapsedCategories.has(cat.category);
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
                      const disabled = isUnsupportedAwsItem(item);
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
                              <img src={item.icon} alt={item.name} width={28} height={28} loading="lazy" />
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
