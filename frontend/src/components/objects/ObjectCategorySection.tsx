'use client';

import { ChevronRight } from 'lucide-react';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import type { PickerCategory } from '@/data/object-catalog';
import ObjectItemButton from './ObjectItemButton';

interface ObjectCategorySectionProps {
  category: PickerCategory;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function ObjectCategorySection({
  category,
  open,
  onOpenChange,
}: ObjectCategorySectionProps) {
  return (
    <Collapsible
      open={open}
      onOpenChange={onOpenChange}
      data-testid={`picker-category-${category.category}`}
    >
      <CollapsibleTrigger
        data-testid={`picker-category-toggle-${category.category}`}
        className="flex w-full cursor-pointer items-center gap-1.5 rounded-md px-2 py-1.5 text-left text-[11px] font-semibold tracking-wide text-muted-foreground uppercase hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
      >
        <ChevronRight
          className="size-3 shrink-0 transition-transform data-[open=true]:rotate-90"
          data-open={open}
        />
        <span className="truncate">{category.category}</span>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="grid grid-cols-[repeat(auto-fill,minmax(64px,1fr))] gap-1 px-1 py-1">
          {category.items.map((item) => (
            <ObjectItemButton key={`${item.category}-${item.name}`} item={item} />
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
