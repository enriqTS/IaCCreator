'use client';

import { useMemo, useState, type ReactNode } from 'react';
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ABBREVIATION_MAP } from '@/data/abbreviation-map';
import {
  ALL_CATEGORIES,
  ALL_CATEGORY_NAMES,
  ALL_ITEMS,
  type PickerCategory,
} from '@/data/object-catalog';
import { smartSearch, sortCategories } from '@/utils/object-search';
import { useLayoutPreferencesStore } from '@/store/layout-preferences-store';
import { useRecentlyUsedStore } from '@/store/recently-used-store';
import ObjectCategorySection from './ObjectCategorySection';
import ObjectItemButton from './ObjectItemButton';

interface ObjectSidebarProps {
  /** Slot for the hamburger menu, which lives in the sidebar header */
  header?: ReactNode;
}

export default function ObjectSidebar({ header }: ObjectSidebarProps) {
  const [search, setSearch] = useState('');
  // Everything starts collapsed so the category icons stay lazily loaded
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(
    () => new Set(ALL_CATEGORY_NAMES),
  );
  const collapsed = useLayoutPreferencesStore((s) => s.objectSidebarCollapsed);
  const toggleSidebar = useLayoutPreferencesStore((s) => s.toggleObjectSidebar);
  const recentItems = useRecentlyUsedStore((s) => s.recentItems);

  const { visibleCategories, categoriesWithMatches } = useMemo(() => {
    const filtered = smartSearch(ALL_ITEMS, search, ABBREVIATION_MAP);
    const keys = new Set(filtered.map((i) => `${i.name}|${i.category}`));

    const base = ALL_CATEGORIES.map((cat) => ({
      ...cat,
      items: cat.items.filter((item) => keys.has(`${item.name}|${item.category}`)),
    })).filter((cat) => cat.items.length > 0);

    const recent: PickerCategory[] =
      recentItems.length > 0 ? [{ category: 'Recently Used', items: recentItems }] : [];

    return {
      visibleCategories: sortCategories([...recent, ...base]),
      categoriesWithMatches: new Set(filtered.map((item) => item.category)),
    };
  }, [search, recentItems]);

  const toggleCategory = (name: string, open: boolean) => {
    setCollapsedCategories((prev) => {
      const next = new Set(prev);
      if (open) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  if (collapsed) {
    return (
      <aside
        data-testid="object-sidebar"
        data-collapsed="true"
        className="flex w-12 shrink-0 flex-col items-center gap-2 border-r border-sidebar-border bg-sidebar py-2 text-sidebar-foreground"
      >
        {header}
        <Button
          data-testid="object-sidebar-toggle"
          variant="ghost"
          size="icon"
          title="Show objects"
          aria-label="Show objects"
          onClick={toggleSidebar}
        >
          <PanelLeftOpen />
        </Button>
        <div className="flex flex-col items-center gap-1 overflow-y-auto">
          {recentItems.map((item) => (
            <ObjectItemButton key={`${item.category}-${item.name}`} item={item} iconOnly />
          ))}
        </div>
      </aside>
    );
  }

  return (
    <aside
      data-testid="object-sidebar"
      data-collapsed="false"
      className="flex w-60 shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground"
    >
      <div className="flex items-center justify-between gap-2 p-2">
        {header}
        <Button
          data-testid="object-sidebar-toggle"
          variant="ghost"
          size="icon"
          title="Hide objects"
          aria-label="Hide objects"
          onClick={toggleSidebar}
        >
          <PanelLeftClose />
        </Button>
      </div>

      <div className="px-2 pb-2">
        <Input
          data-testid="object-sidebar-search"
          type="text"
          placeholder="Search objects..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="flex-1 overflow-y-auto px-1 pb-2">
        {visibleCategories.length === 0 && (
          <p className="px-2 py-3 text-sm text-muted-foreground">No items found</p>
        )}
        {visibleCategories.map((cat) => {
          // A search term expands the categories it matched so the hits are visible
          const open =
            search.trim() !== '' && categoriesWithMatches.has(cat.category)
              ? true
              : !collapsedCategories.has(cat.category);
          return (
            <ObjectCategorySection
              key={cat.category}
              category={cat}
              open={open}
              onOpenChange={(next) => toggleCategory(cat.category, next)}
            />
          );
        })}
      </div>
    </aside>
  );
}
