'use client';

import { Pin } from 'lucide-react';
import { getItemIcon } from '@/data/shape-icons';
import { isUnsupportedAwsItem, toolsMatch, type PickerItem } from '@/data/object-catalog';
import { useDiagramStore } from '@/store/diagram-store';
import { useEditorDomainStore } from '@/store/editor-domain-store';
import { useRecentlyUsedStore } from '@/store/recently-used-store';
import { usePinnedObjectsStore, pickerItemKey } from '@/store/pinned-objects-store';
import { cn } from '@/lib/utils';

interface ObjectItemButtonProps {
  item: PickerItem;
  /** Render as a bare icon without its label or pin, for the collapsed rail */
  iconOnly?: boolean;
}

export default function ObjectItemButton({ item, iconOnly = false }: ObjectItemButtonProps) {
  const activeTool = useDiagramStore((s) => s.activeTool);
  const setActiveTool = useDiagramStore((s) => s.setActiveTool);
  const addRecentItem = useRecentlyUsedStore((s) => s.addRecentItem);
  const pinnedItems = usePinnedObjectsStore((s) => s.pinnedItems);
  const togglePin = usePinnedObjectsStore((s) => s.togglePin);
  const supportedServices = useEditorDomainStore((s) => s.supportedServices);

  const serviceType = typeof item.tool === 'object' && item.tool.type === 'place-service'
    ? item.tool.serviceType
    : null;
  const disabled = isUnsupportedAwsItem(item)
    || (serviceType !== null && (supportedServices === null || !supportedServices.has(serviceType)));
  const active = !disabled && toolsMatch(activeTool, item.tool);
  const pinned = pinnedItems.some((p) => pickerItemKey(p) === pickerItemKey(item));

  const icon = item.icon ? (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={item.icon} alt={item.name} width={32} height={32} loading="lazy" />
  ) : (
    getItemIcon(item.name) || (
      <span className="flex size-8 items-center justify-center rounded-md bg-sidebar-accent text-[11px] font-semibold select-none">
        {item.name.slice(0, 2)}
      </span>
    )
  );

  if (iconOnly) {
    return (
      <button
        data-testid={`picker-item-${item.name}`}
        title={item.name}
        disabled={disabled}
        aria-pressed={active}
        onClick={() => {
          addRecentItem(item);
          setActiveTool(item.tool);
        }}
        className={cn(
          'flex size-9 shrink-0 items-center justify-center rounded-md [&_img]:size-6 [&_svg]:size-6',
          disabled ? 'cursor-default opacity-40' : 'cursor-pointer hover:bg-sidebar-accent',
          active && 'bg-sidebar-primary text-sidebar-primary-foreground',
        )}
      >
        {icon}
      </button>
    );
  }

  return (
    <div
      className={cn(
        'group/tile relative flex min-h-[74px] min-w-0 flex-col items-center gap-1 rounded-md p-1.5 transition-colors',
        disabled
          ? 'cursor-default opacity-40'
          : 'cursor-pointer hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
        active && 'bg-sidebar-primary text-sidebar-primary-foreground',
      )}
    >
      <button
        data-testid={`picker-item-${item.name}`}
        title={item.name}
        disabled={disabled}
        aria-pressed={active}
        onClick={() => {
          addRecentItem(item);
          setActiveTool(item.tool);
        }}
        className="flex min-w-0 flex-1 cursor-[inherit] flex-col items-center gap-1 disabled:pointer-events-none"
      >
        <span className="flex size-8 shrink-0 items-center justify-center">{icon}</span>
        <span className="line-clamp-2 w-full text-center text-[11px] leading-tight text-pretty">
          {item.name}
        </span>
      </button>
      {!disabled && (
        <button
          data-testid={`picker-pin-${item.name}`}
          title={pinned ? 'Unpin' : 'Pin to the top'}
          aria-label={pinned ? `Unpin ${item.name}` : `Pin ${item.name}`}
          aria-pressed={pinned}
          onClick={() => togglePin(item)}
          className={cn(
            'absolute top-0.5 right-0.5 flex size-[18px] items-center justify-center rounded-sm text-muted-foreground opacity-0 transition-opacity hover:bg-white/12 hover:text-foreground focus-visible:opacity-100 group-hover/tile:opacity-100',
            pinned && 'text-sidebar-ring opacity-100',
          )}
        >
          <Pin className="size-3" fill={pinned ? 'currentColor' : 'none'} />
        </button>
      )}
    </div>
  );
}
