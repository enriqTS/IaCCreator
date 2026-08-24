'use client';

import { getItemIcon } from '@/data/shape-icons';
import { isUnsupportedAwsItem, type PickerItem } from '@/data/object-catalog';
import { useDiagramStore } from '@/store/diagram-store';
import { useRecentlyUsedStore } from '@/store/recently-used-store';
import type { Tool } from '@/types/diagram';
import { cn } from '@/lib/utils';

function toolsMatch(a: Tool, b: Tool): boolean {
  if (typeof a === 'string' || typeof b === 'string') return a === b;
  return JSON.stringify(a) === JSON.stringify(b);
}

interface ObjectItemButtonProps {
  item: PickerItem;
  /** Render as a bare icon without its label, for the collapsed rail */
  iconOnly?: boolean;
}

export default function ObjectItemButton({ item, iconOnly = false }: ObjectItemButtonProps) {
  const activeTool = useDiagramStore((s) => s.activeTool);
  const setActiveTool = useDiagramStore((s) => s.setActiveTool);
  const addRecentItem = useRecentlyUsedStore((s) => s.addRecentItem);

  const disabled = isUnsupportedAwsItem(item);
  const active = !disabled && toolsMatch(activeTool, item.tool);

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
        'flex min-w-0 flex-col items-center justify-center gap-0.5 rounded-md p-1 transition-colors',
        disabled
          ? 'cursor-default opacity-40'
          : 'cursor-pointer hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
        active && 'bg-sidebar-primary text-sidebar-primary-foreground',
      )}
    >
      <span className="flex size-7 shrink-0 items-center justify-center">
        {item.icon ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={item.icon} alt={item.name} width={28} height={28} loading="lazy" />
        ) : (
          getItemIcon(item.name) || (
            <span className="text-xs leading-none font-semibold select-none">
              {item.name.slice(0, 2)}
            </span>
          )
        )}
      </span>
      {!iconOnly && (
        <span className="w-full truncate text-center text-[9px] leading-tight">
          {item.name}
        </span>
      )}
    </button>
  );
}
