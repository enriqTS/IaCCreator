'use client';

import { useDiagramStore } from '@/store/diagram-store';
import { Button } from '@/components/ui/button';

interface ZOrderControlsProps {
  objectId: string;
}

export default function ZOrderControls({ objectId }: ZOrderControlsProps) {
  const bringToFront = useDiagramStore((s) => s.bringToFront);
  const sendToBack = useDiagramStore((s) => s.sendToBack);
  const bringForward = useDiagramStore((s) => s.bringForward);
  const sendBackward = useDiagramStore((s) => s.sendBackward);

  return (
    <div data-testid="z-order-controls" className="flex gap-2 items-center">
      <Button
        data-testid="bring-to-front-button"
        variant="outline"
        size="sm"
        onClick={() => bringToFront(objectId)}
      >
        Bring to Front
      </Button>
      <Button
        data-testid="bring-forward-button"
        variant="outline"
        size="sm"
        onClick={() => bringForward(objectId)}
      >
        Bring Forward
      </Button>
      <Button
        data-testid="send-backward-button"
        variant="outline"
        size="sm"
        onClick={() => sendBackward(objectId)}
      >
        Send Backward
      </Button>
      <Button
        data-testid="send-to-back-button"
        variant="outline"
        size="sm"
        onClick={() => sendToBack(objectId)}
      >
        Send to Back
      </Button>
    </div>
  );
}
