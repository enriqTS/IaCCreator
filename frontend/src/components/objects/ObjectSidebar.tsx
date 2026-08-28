'use client';

import { useCallback, useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent, type ReactNode } from 'react';
import { PanelLeftClose, PanelRightClose, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ABBREVIATION_MAP } from '@/data/abbreviation-map';
import { categoriesWithContainers } from '@/data/object-catalog';
import { smartSearch, sortCategories } from '@/utils/object-search';
import { useDiagramStore } from '@/store/diagram-store';
import { useLayoutPreferencesStore } from '@/store/layout-preferences-store';
import { useEditorDomainStore } from '@/store/editor-domain-store';
import ObjectArmedBar from './ObjectArmedBar';
import ObjectCategorySection from './ObjectCategorySection';
import ObjectShortlist from './ObjectShortlist';
import ObjectSidebarRail from './ObjectSidebarRail';

interface ObjectSidebarProps {
  /** Slot for the hamburger menu, which lives in the sidebar header */
  header?: ReactNode;
}

export default function ObjectSidebar({ header }: ObjectSidebarProps) {
  const [search, setSearch] = useState('');
  const [openCategories, setOpenCategories] = useState<Set<string>>(() => new Set());
  const searchRef = useRef<HTMLInputElement>(null);
  const collapsed = useLayoutPreferencesStore((s) => s.objectSidebarCollapsed);
  const setCollapsed = useLayoutPreferencesStore((s) => s.setObjectSidebarCollapsed);
  const position = useLayoutPreferencesStore((s) => s.objectSidebarPosition);
  const width = useLayoutPreferencesStore((s) => s.objectSidebarWidth);
  const setWidth = useLayoutPreferencesStore((s) => s.setObjectSidebarWidth);
  const containerDefinitions = useEditorDomainStore((s) => s.semanticContainerDefinitions);
  const allCategories = useMemo(
    () => categoriesWithContainers(containerDefinitions),
    [containerDefinitions],
  );
  const allItems = useMemo(() => allCategories.flatMap((category) => category.items), [allCategories]);

  const startResize = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = width;
    const handleMove = (moveEvent: PointerEvent) => {
      const delta = moveEvent.clientX - startX;
      setWidth(startWidth + (position === 'left' ? delta : -delta));
    };
    const handleUp = () => {
      window.removeEventListener('pointermove', handleMove);
      window.removeEventListener('pointerup', handleUp);
    };
    window.addEventListener('pointermove', handleMove);
    window.addEventListener('pointerup', handleUp);
  }, [position, setWidth, width]);

  const { categories, matchCount } = useMemo(() => {
    const term = search.trim();
    if (!term) return { categories: sortCategories(allCategories), matchCount: 0 };

    const matches = smartSearch(allItems, term, ABBREVIATION_MAP);
    const keys = new Set(matches.map((i) => `${i.name}|${i.category}`));
    const filtered = allCategories.map((cat) => ({
      ...cat,
      items: cat.items.filter((item) => keys.has(`${item.name}|${item.category}`)),
    })).filter((cat) => cat.items.length > 0);
    return { categories: sortCategories(filtered), matchCount: matches.length };
  }, [allCategories, allItems, search]);

  const searching = search.trim() !== '';

  const focusSearch = useCallback(() => {
    setCollapsed(false);
    // The field only exists once the expanded sidebar has rendered
    requestAnimationFrame(() => searchRef.current?.focus());
  }, [setCollapsed]);

  // A catalog this large is searched more than it is browsed, so give it a key
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key !== '/' || e.ctrlKey || e.metaKey || e.altKey) return;
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target?.isContentEditable) return;
      if (useDiagramStore.getState().configOverlayTargetId) return;
      e.preventDefault();
      focusSearch();
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [focusSearch]);

  const toggleCategory = (name: string, open: boolean) => {
    setOpenCategories((prev) => {
      const next = new Set(prev);
      if (open) next.add(name);
      else next.delete(name);
      return next;
    });
  };

  if (collapsed) {
    return <ObjectSidebarRail header={header} onExpand={focusSearch} />;
  }

  return (
    <aside
      data-testid="object-sidebar"
      data-collapsed="false"
      data-position={position}
      className={`relative order-2 flex shrink-0 flex-col bg-sidebar text-sidebar-foreground ${position === 'left' ? 'order-first border-r border-sidebar-border' : 'border-l border-sidebar-border'}`}
      style={{ width }}
    >
      <div
        role="separator"
        aria-label="Resize object sidebar"
        aria-orientation="vertical"
        data-testid="object-sidebar-resize-handle"
        onPointerDown={startResize}
        className={`absolute inset-y-0 z-10 w-1 cursor-col-resize ${position === 'left' ? '-right-0.5' : '-left-0.5'}`}
      />
      <div className="flex items-center justify-between gap-2 p-2">
        {header}
        <Button
          data-testid="object-sidebar-toggle"
          variant="ghost"
          size="icon"
          title="Hide objects"
          aria-label="Hide objects"
          onClick={() => setCollapsed(true)}
        >
          {position === 'left' ? <PanelLeftClose /> : <PanelRightClose />}
        </Button>
      </div>

      <div className="relative px-2 pb-2.5">
        <Search className="pointer-events-none absolute top-2.5 left-4 size-4 text-muted-foreground" />
        <Input
          ref={searchRef}
          data-testid="object-sidebar-search"
          type="text"
          placeholder={`Search ${allItems.length} objects`}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pr-9 pl-8"
        />
        <kbd className="pointer-events-none absolute top-2.5 right-4 flex h-[18px] min-w-[18px] items-center justify-center rounded-sm border border-input bg-input/30 px-1 text-[10px] text-muted-foreground">
          /
        </kbd>
      </div>

      {!searching && (
        <>
          <ObjectShortlist />
          <span className="mx-2.5 mb-2 h-px bg-sidebar-border" />
        </>
      )}

      {searching && (
        <p data-testid="object-search-count" className="px-2.5 pb-1.5 text-[10px] text-muted-foreground tabular-nums">
          {matchCount === 1 ? '1 match' : `${matchCount} matches`}
        </p>
      )}

      <div className="flex-1 overflow-y-auto px-1 pb-2">
        {categories.length === 0 && (
          <p className="px-2 py-3 text-sm text-muted-foreground">No items found</p>
        )}
        {categories.map((cat) => (
          <ObjectCategorySection
            key={cat.category}
            category={cat}
            open={searching || openCategories.has(cat.category)}
            onOpenChange={(next) => toggleCategory(cat.category, next)}
          />
        ))}
      </div>

      <ObjectArmedBar />
    </aside>
  );
}
