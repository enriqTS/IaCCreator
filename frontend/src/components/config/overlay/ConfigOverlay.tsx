'use client';

import { useDiagramStore } from '@/store/diagram-store';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { resolveConfigOverlayPanel } from './overlay-registry';

/**
 * The single configuration surface: a focused panel over a dimmed canvas.
 *
 * It opens only on placing an object, double-clicking one, or the context menu,
 * and closes on the X, a click outside, or Escape. It owns no per-type knowledge:
 * the registry decides which panel an object contributes, and returns nothing
 * when there is nothing to configure.
 */
export default function ConfigOverlay() {
  const targetId = useDiagramStore((s) => s.configOverlayTargetId);
  const closeConfigOverlay = useDiagramStore((s) => s.closeConfigOverlay);
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);
  const connectors = useDiagramStore((s) => s.connectors);

  const target = targetId ? canvasObjects.get(targetId) ?? null : null;
  const panel = resolveConfigOverlayPanel(target, { canvasObjects, connectors });

  return (
    <Dialog
      open={panel !== null}
      onOpenChange={(open) => {
        if (!open) closeConfigOverlay();
      }}
    >
      {panel && (
        <DialogContent
          data-testid="config-overlay"
          data-panel-key={panel.key}
          className="grid max-h-[85vh] grid-cols-[minmax(0,1fr)] grid-rows-[auto_1fr] gap-0 overflow-hidden p-0 sm:max-w-2xl"
        >
          <DialogHeader className="border-b px-6 py-4 pr-14">
            <DialogTitle data-testid="config-overlay-title" className="truncate text-base">
              {panel.title}
            </DialogTitle>
            <DialogDescription className="truncate text-xs">
              {panel.subtitle}
            </DialogDescription>
          </DialogHeader>

          {/* min-w-0 so a wide tab strip scrolls inside the modal instead of stretching it */}
          <div
            data-testid="config-overlay-content"
            className="min-w-0 overflow-y-auto px-6 py-4"
          >
            {panel.content}
          </div>
        </DialogContent>
      )}
    </Dialog>
  );
}
