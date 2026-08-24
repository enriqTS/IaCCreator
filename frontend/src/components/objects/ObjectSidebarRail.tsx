'use client';

import { PanelLeftOpen, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { usePinnedObjectsStore, pickerItemKey } from '@/store/pinned-objects-store';
import { useRecentlyUsedStore } from '@/store/recently-used-store';
import ObjectItemButton from './ObjectItemButton';

const MAX_RAIL_ITEMS = 8;

interface ObjectSidebarRailProps {
  /** Slot for the hamburger menu, which must stay reachable while collapsed */
  header?: React.ReactNode;
  onExpand: () => void;
}

export default function ObjectSidebarRail({ header, onExpand }: ObjectSidebarRailProps) {
  const pinnedItems = usePinnedObjectsStore((s) => s.pinnedItems);
  const recentItems = useRecentlyUsedStore((s) => s.recentItems);

  const pinnedKeys = new Set(pinnedItems.map(pickerItemKey));
  const items = [
    ...pinnedItems,
    ...recentItems.filter((r) => !pinnedKeys.has(pickerItemKey(r))),
  ].slice(0, MAX_RAIL_ITEMS);

  return (
    <aside
      data-testid="object-sidebar"
      data-collapsed="true"
      className="flex w-12 shrink-0 flex-col items-center gap-1 border-r border-sidebar-border bg-sidebar py-2 text-sidebar-foreground"
    >
      {header}
      <Button
        data-testid="object-sidebar-search-open"
        variant="ghost"
        size="icon"
        title="Search objects"
        aria-label="Search objects"
        onClick={onExpand}
      >
        <Search />
      </Button>
      <span className="my-1 h-px w-7 bg-sidebar-border" />
      <div className="flex flex-col items-center gap-1 overflow-y-auto">
        {items.map((item) => (
          <ObjectItemButton key={`${item.category}-${item.name}`} item={item} iconOnly />
        ))}
      </div>
      <span className="flex-1" />
      <Button
        data-testid="object-sidebar-toggle"
        variant="ghost"
        size="icon"
        title="Show objects"
        aria-label="Show objects"
        onClick={onExpand}
      >
        <PanelLeftOpen />
      </Button>
    </aside>
  );
}
