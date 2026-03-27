'use client';

import { useEffect, useRef } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import {
  ClipboardPaste,
  MousePointerSquareDashed,
  Maximize,
} from 'lucide-react';

interface CanvasContextMenuProps {
  menu: {
    x: number;
    y: number;
    canvasPosition: { x: number; y: number };
  };
  onClose: () => void;
}

export default function CanvasContextMenu({ menu, onClose }: CanvasContextMenuProps) {
  const clipboard = useDiagramStore((s) => s.clipboard);
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);
  const pasteObjects = useDiagramStore((s) => s.pasteObjects);
  const selectAllObjects = useDiagramStore((s) => s.selectAllObjects);
  const fitToScreen = useDiagramStore((s) => s.fitToScreen);

  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) onClose();
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  useEffect(() => {
    function handleEscape(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  const hasObjects = canvasObjects.size > 0;
  const hasClipboard = clipboard.length > 0;

  const itemClass = 'flex items-center gap-2 px-3 py-1.5 text-sm rounded-sm cursor-default select-none hover:bg-accent hover:text-accent-foreground outline-none';
  const disabledClass = 'opacity-50 pointer-events-none';

  function Item({ onClick, children, disabled }: { onClick: () => void; children: React.ReactNode; disabled?: boolean }) {
    return (
      <div
        role="menuitem"
        tabIndex={-1}
        className={`${itemClass} ${disabled ? disabledClass : ''}`}
        onClick={disabled ? undefined : onClick}
      >
        {children}
      </div>
    );
  }

  return (
    <div
      ref={menuRef}
      data-testid="canvas-context-menu-canvas"
      role="menu"
      style={{ position: 'fixed', top: menu.y, left: menu.x, zIndex: 9999 }}
      className="min-w-[160px] rounded-md border bg-popover p-1 text-popover-foreground shadow-md"
    >
      <Item disabled={!hasClipboard} onClick={() => { pasteObjects(menu.canvasPosition); onClose(); }}>
        <ClipboardPaste className="size-4" /> Paste
      </Item>
      <Item disabled={!hasObjects} onClick={() => { selectAllObjects(); onClose(); }}>
        <MousePointerSquareDashed className="size-4" /> Select All
      </Item>
      <Item disabled={!hasObjects} onClick={() => { fitToScreen({ width: window.innerWidth, height: window.innerHeight }); onClose(); }}>
        <Maximize className="size-4" /> Fit to Screen
      </Item>
    </div>
  );
}
