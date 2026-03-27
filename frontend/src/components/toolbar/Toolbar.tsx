'use client';

import { useDiagramStore } from '@/store/diagram-store';
import { useLayoutPreferencesStore } from '@/store/layout-preferences-store';
import { Button } from '@/components/ui/button';
import AWSServicePicker from './AWSServicePicker';

export default function Toolbar() {
  const activeTool = useDiagramStore((s) => s.activeTool);
  const setActiveTool = useDiagramStore((s) => s.setActiveTool);
  const undo = useDiagramStore((s) => s.undo);
  const redo = useDiagramStore((s) => s.redo);
  const canUndo = useDiagramStore((s) => s.canUndo);
  const canRedo = useDiagramStore((s) => s.canRedo);
  const toolbarPosition = useLayoutPreferencesStore((s) => s.toolbarPosition);

  const isPointer = activeTool === 'pointer';
  const isConnector = activeTool === 'connector';
  const isLine = activeTool === 'line';
  const isRectangle =
    typeof activeTool === 'object' &&
    activeTool.type === 'place-shape' &&
    activeTool.shape === 'rectangle';
  const isEllipse =
    typeof activeTool === 'object' &&
    activeTool.type === 'place-shape' &&
    activeTool.shape === 'ellipse';

  const positionStyle: React.CSSProperties =
    toolbarPosition === 'top'
      ? { top: 16, left: '50%', transform: 'translateX(-50%)' }
      : { bottom: 16, left: '50%', transform: 'translateX(-50%)' };

  return (
    <div
      data-testid="toolbar"
      style={{
        position: 'fixed',
        ...positionStyle,
        zIndex: 50,
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        background: '#1e1e1e',
        borderRadius: 12,
        padding: '6px 8px',
        boxShadow: '0 4px 24px rgba(0, 0, 0, 0.5)',
      }}
    >
      {/* Tool buttons */}
      <Button
        variant={isPointer ? 'secondary' : 'ghost'}
        size="icon"
        title="Pointer (V)"
        onClick={() => setActiveTool('pointer')}
      >
        ↖
      </Button>
      <Button
        variant={isConnector ? 'secondary' : 'ghost'}
        size="icon"
        title="Connector (C)"
        onClick={() => setActiveTool('connector')}
      >
        →
      </Button>
      <Button
        variant={isLine ? 'secondary' : 'ghost'}
        size="icon"
        title="Line (L)"
        onClick={() => setActiveTool('line')}
        data-testid="tool-line"
      >
        ╱
      </Button>
      <Button
        variant={isRectangle ? 'secondary' : 'ghost'}
        size="icon"
        title="Rectangle (R)"
        onClick={() => setActiveTool({ type: 'place-shape', shape: 'rectangle' })}
        data-testid="tool-rectangle"
      >
        □
      </Button>
      <Button
        variant={isEllipse ? 'secondary' : 'ghost'}
        size="icon"
        title="Ellipse (E)"
        onClick={() => setActiveTool({ type: 'place-shape', shape: 'ellipse' })}
        data-testid="tool-ellipse"
      >
        ○
      </Button>

      {/* Separator */}
      <div
        style={{
          width: 1,
          height: 24,
          background: '#444',
          margin: '0 4px',
        }}
      />

      {/* Undo / Redo */}
      <Button
        variant="ghost"
        size="icon"
        title="Undo (Ctrl+Z)"
        disabled={!canUndo}
        onClick={undo}
      >
        ↩
      </Button>
      <Button
        variant="ghost"
        size="icon"
        title="Redo (Ctrl+Shift+Z)"
        disabled={!canRedo}
        onClick={redo}
      >
        ↪
      </Button>

      {/* Separator */}
      <div
        style={{
          width: 1,
          height: 24,
          background: '#444',
          margin: '0 4px',
        }}
      />

      {/* AWS Service Picker */}
      <AWSServicePicker />
    </div>
  );
}
