'use client';

import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getItemIcon } from '@/data/shape-icons';
import { findItemForTool } from '@/data/object-catalog';
import { useDiagramStore } from '@/store/diagram-store';
import { useEditorDomainStore } from '@/store/editor-domain-store';

export default function ObjectArmedBar() {
  const activeTool = useDiagramStore((s) => s.activeTool);
  const setActiveTool = useDiagramStore((s) => s.setActiveTool);
  const containerDefinitions = useEditorDomainStore((s) => s.semanticContainerDefinitions);

  const item = findItemForTool(activeTool) ?? (
    typeof activeTool === 'object' && activeTool.type === 'place-semantic-container'
      ? {
          name: containerDefinitions.find(
            (definition) => definition.container_type === activeTool.containerType,
          )?.display_name ?? activeTool.containerType,
          category: 'Architecture Scopes',
          tool: activeTool,
        }
      : null
  );
  if (!item) return null;

  return (
    <div
      data-testid="object-armed-bar"
      className="flex items-center gap-2 border-t border-sidebar-border p-2"
    >
      <span className="flex size-6 shrink-0 items-center justify-center [&_img]:size-6 [&_svg]:size-6">
        {item.icon ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={item.icon} alt="" width={24} height={24} />
        ) : (
          getItemIcon(item.name)
        )}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-xs font-medium">Placing {item.name}</span>
        <span className="block text-[10px] text-muted-foreground">
          Click the canvas · Esc to cancel
        </span>
      </span>
      <Button
        data-testid="object-armed-cancel"
        variant="ghost"
        size="icon-xs"
        title="Cancel placement"
        aria-label="Cancel placement"
        onClick={() => setActiveTool('pointer')}
      >
        <X />
      </Button>
    </div>
  );
}
