'use client';

import { useDiagramStore } from '@/store/diagram-store';
import AWSServicePicker from './AWSServicePicker';

function ToolButton({
  label,
  title,
  active,
  disabled,
  onClick,
  'data-testid': dataTestId,
}: {
  label: string;
  title: string;
  active: boolean;
  disabled?: boolean;
  onClick: () => void;
  'data-testid'?: string;
}) {
  return (
    <button
      title={title}
      disabled={disabled || false}
      onClick={onClick}
      data-testid={dataTestId}
      style={{
        width: 36,
        height: 36,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: 8,
        border: 'none',
        cursor: disabled ? 'default' : 'pointer',
        fontSize: 18,
        background: active ? 'rgba(59, 130, 246, 0.3)' : 'transparent',
        color: disabled ? 'rgba(255, 255, 255, 0.3)' : '#e5e5e5',
        opacity: disabled ? 0.5 : 1,
        transition: 'background 0.15s',
      }}
      onMouseEnter={(e) => {
        if (!active && !disabled) {
          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
        }
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = active
          ? 'rgba(59, 130, 246, 0.3)'
          : 'transparent';
      }}
    >
      {label}
    </button>
  );
}

export default function Toolbar() {
  const activeTool = useDiagramStore((s) => s.activeTool);
  const setActiveTool = useDiagramStore((s) => s.setActiveTool);
  const undo = useDiagramStore((s) => s.undo);
  const redo = useDiagramStore((s) => s.redo);
  const canUndo = useDiagramStore((s) => s.canUndo);
  const canRedo = useDiagramStore((s) => s.canRedo);

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

  return (
    <div
      data-testid="toolbar"
      style={{
        position: 'fixed',
        top: 16,
        left: '50%',
        transform: 'translateX(-50%)',
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
      <ToolButton
        label="↖"
        title="Pointer (V)"
        active={isPointer}
        onClick={() => setActiveTool('pointer')}
      />
      <ToolButton
        label="→"
        title="Connector (C)"
        active={isConnector}
        onClick={() => setActiveTool('connector')}
      />
      <ToolButton
        label="╱"
        title="Line (L)"
        active={isLine}
        onClick={() => setActiveTool('line')}
        data-testid="tool-line"
      />
      <ToolButton
        label="□"
        title="Rectangle (R)"
        active={isRectangle}
        onClick={() => setActiveTool({ type: 'place-shape', shape: 'rectangle' })}
        data-testid="tool-rectangle"
      />
      <ToolButton
        label="○"
        title="Ellipse (E)"
        active={isEllipse}
        onClick={() => setActiveTool({ type: 'place-shape', shape: 'ellipse' })}
        data-testid="tool-ellipse"
      />

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
      <ToolButton
        label="↩"
        title="Undo (Ctrl+Z)"
        active={false}
        disabled={!canUndo}
        onClick={undo}
      />
      <ToolButton
        label="↪"
        title="Redo (Ctrl+Shift+Z)"
        active={false}
        disabled={!canRedo}
        onClick={redo}
      />

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
