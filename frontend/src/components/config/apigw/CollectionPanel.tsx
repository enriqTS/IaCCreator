'use client';

import { Plus, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface CollectionPanelProps<T extends { id: string }> {
  items: T[];
  selectedItemId: string | null;
  onSelect: (id: string) => void;
  onAdd: () => void;
  onRemove: (id: string) => void;
  renderSummary: (item: T) => React.ReactNode;
  addLabel: string;
  emptyMessage: string;
  canRemove?: (item: T) => boolean;
  removeDisabledTooltip?: string;
}

export default function CollectionPanel<T extends { id: string }>({
  items,
  selectedItemId,
  onSelect,
  onAdd,
  onRemove,
  renderSummary,
  addLabel,
  emptyMessage,
  canRemove,
  removeDisabledTooltip,
}: CollectionPanelProps<T>) {
  return (
    <div className="flex w-full flex-col gap-2">
      {/* Scrollable item list */}
      {items.length === 0 ? (
        <p className="py-4 text-center text-sm text-muted-foreground">
          {emptyMessage}
        </p>
      ) : (
        <div className="flex max-h-64 flex-col gap-1 overflow-y-auto">
          {items.map((item) => {
            const isSelected = item.id === selectedItemId;
            const removable = canRemove ? canRemove(item) : true;

            return (
              <div
                key={item.id}
                role="button"
                tabIndex={0}
                onClick={() => onSelect(item.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onSelect(item.id);
                  }
                }}
                className={cn(
                  'flex w-full cursor-pointer items-center justify-between rounded-md border px-3 py-2 text-sm transition-colors',
                  'bg-muted/30 border-border hover:bg-muted/60',
                  isSelected && 'ring-2 ring-primary bg-muted/50 border-primary/50'
                )}
              >
                <span className="min-w-0 flex-1 truncate">
                  {renderSummary(item)}
                </span>

                {removable ? (
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemove(item.id);
                    }}
                    aria-label="Remove item"
                    className="ml-2 shrink-0 text-muted-foreground hover:text-destructive"
                  >
                    <X className="size-3.5" />
                  </Button>
                ) : (
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon-xs"
                          disabled
                          aria-label="Cannot remove item"
                          className="ml-2 shrink-0"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <X className="size-3.5" />
                        </Button>
                      </TooltipTrigger>
                      {removeDisabledTooltip && (
                        <TooltipContent>
                          {removeDisabledTooltip}
                        </TooltipContent>
                      )}
                    </Tooltip>
                  </TooltipProvider>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Add button */}
      <Button
        variant="outline"
        size="sm"
        onClick={onAdd}
        className="w-full"
      >
        <Plus className="size-4" />
        {addLabel}
      </Button>
    </div>
  );
}
