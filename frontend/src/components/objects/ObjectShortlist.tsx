'use client';

import { Pin } from 'lucide-react';
import { usePinnedObjectsStore } from '@/store/pinned-objects-store';
import { useRecentlyUsedStore } from '@/store/recently-used-store';
import ObjectItemButton from './ObjectItemButton';

const MAX_RECENT_SHOWN = 6;

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <p className="flex items-center gap-1.5 px-0.5 pb-1 text-[10px] font-semibold tracking-[0.06em] text-muted-foreground uppercase">
      {children}
    </p>
  );
}

// The shortlist is what keeps a several-hundred-object catalog usable day to day
export default function ObjectShortlist() {
  const pinnedItems = usePinnedObjectsStore((s) => s.pinnedItems);
  const recentItems = useRecentlyUsedStore((s) => s.recentItems);

  const recent = recentItems.slice(0, MAX_RECENT_SHOWN);

  return (
    <div data-testid="object-shortlist">
      <div className="px-2 pb-2">
        <Eyebrow>
          <Pin className="size-2.5" />
          Pinned
        </Eyebrow>
        {pinnedItems.length > 0 ? (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(70px,1fr))] gap-1">
            {pinnedItems.map((item) => (
              <ObjectItemButton key={`${item.category}-${item.name}`} item={item} />
            ))}
          </div>
        ) : (
          <p className="px-0.5 text-[10px] leading-relaxed text-muted-foreground">
            Hover any object and press the pin to keep it here.
          </p>
        )}
      </div>

      {recent.length > 0 && (
        <div className="px-2 pb-2">
          <Eyebrow>Recent</Eyebrow>
          <div className="grid grid-cols-[repeat(auto-fill,minmax(70px,1fr))] gap-1">
            {recent.map((item) => (
              <ObjectItemButton key={`${item.category}-${item.name}`} item={item} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
