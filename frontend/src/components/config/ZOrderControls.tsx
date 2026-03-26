'use client';

import { useDiagramStore } from '@/store/diagram-store';

interface ZOrderControlsProps {
  objectId: string;
}

export default function ZOrderControls({ objectId }: ZOrderControlsProps) {
  const bringToFront = useDiagramStore((s) => s.bringToFront);
  const sendToBack = useDiagramStore((s) => s.sendToBack);
  const bringForward = useDiagramStore((s) => s.bringForward);
  const sendBackward = useDiagramStore((s) => s.sendBackward);

  const buttonStyle: React.CSSProperties = {
    padding: '4px 10px',
    fontSize: '12px',
    color: 'rgba(255, 255, 255, 0.8)',
    backgroundColor: 'transparent',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    borderRadius: '4px',
    cursor: 'pointer',
  };

  return (
    <div data-testid="z-order-controls" style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
      <button
        data-testid="bring-to-front-button"
        onClick={() => bringToFront(objectId)}
        style={buttonStyle}
      >
        Bring to Front
      </button>
      <button
        data-testid="bring-forward-button"
        onClick={() => bringForward(objectId)}
        style={buttonStyle}
      >
        Bring Forward
      </button>
      <button
        data-testid="send-backward-button"
        onClick={() => sendBackward(objectId)}
        style={buttonStyle}
      >
        Send Backward
      </button>
      <button
        data-testid="send-to-back-button"
        onClick={() => sendToBack(objectId)}
        style={buttonStyle}
      >
        Send to Back
      </button>
    </div>
  );
}
