'use client';

import { useState } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { useLayoutPreferencesStore } from '@/store/layout-preferences-store';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { resolveConfigOverlayPanel } from './overlay-registry';

/**
 * The single configuration surface, opened by selection.
 *
 * It owns no per-type knowledge: the registry decides which panel a selected
 * object contributes, and returns nothing when there is nothing to configure.
 */
export default function ConfigOverlay() {
  const selectedObjectIds = useDiagramStore((s) => s.selectedObjectIds);
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);
  const connectors = useDiagramStore((s) => s.connectors);
  const sidebarSide = useLayoutPreferencesStore((s) => s.sidebarSide);

  const selectedId = selectedObjectIds.size === 1 ? Array.from(selectedObjectIds)[0] : null;
  const selected = selectedId ? canvasObjects.get(selectedId) ?? null : null;
  const panel = resolveConfigOverlayPanel(selected, { canvasObjects, connectors });

  // Dismissal lasts until a different thing is selected, so the overlay never nags
  const [dismissedKey, setDismissedKey] = useState<string | null>(null);

  if (!panel || dismissedKey === panel.key) return null;

  // Sit opposite the sidebar so both surfaces stay reachable
  const isLeft = sidebarSide === 'right';

  return (
    <Card
      data-testid="config-overlay"
      data-panel-key={panel.key}
      className={cn(
        'fixed top-16 bottom-16 z-40 flex w-[min(560px,45vw)] gap-0 overflow-hidden py-0',
        isLeft ? 'left-6' : 'right-6',
      )}
    >
      <CardHeader className="flex-row items-start justify-between gap-2 border-b px-4 py-3">
        <div className="flex flex-col gap-0.5 overflow-hidden">
          <CardTitle data-testid="config-overlay-title" className="truncate text-sm">
            {panel.title}
          </CardTitle>
          <span className="truncate text-xs text-muted-foreground">{panel.subtitle}</span>
        </div>
        <Button
          variant="ghost"
          size="icon-sm"
          data-testid="config-overlay-close"
          onClick={() => setDismissedKey(panel.key)}
          aria-label="Close configuration"
        >
          <X className="size-4" />
        </Button>
      </CardHeader>

      <CardContent data-testid="config-overlay-content" className="flex-1 overflow-y-auto p-4">
        {panel.content}
      </CardContent>
    </Card>
  );
}
