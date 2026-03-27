'use client';

import { useEffect, useRef } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
} from '@/components/ui/dropdown-menu';
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
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
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

  return (
    <div
      ref={menuRef}
      data-testid="canvas-context-menu-canvas"
      style={{
        position: 'fixed',
        top: menu.y,
        left: menu.x,
        zIndex: 100,
      }}
    >
      <DropdownMenu open onOpenChange={(open) => { if (!open) onClose(); }}>
        <DropdownMenuContent align="start" side="bottom" sideOffset={0}>
          <DropdownMenuItem
            disabled={!hasClipboard}
            onSelect={() => { pasteObjects(menu.canvasPosition); onClose(); }}
          >
            <ClipboardPaste className="size-4" />
            Paste
          </DropdownMenuItem>
          <DropdownMenuItem
            disabled={!hasObjects}
            onSelect={() => { selectAllObjects(); onClose(); }}
          >
            <MousePointerSquareDashed className="size-4" />
            Select All
          </DropdownMenuItem>
          <DropdownMenuItem
            disabled={!hasObjects}
            onSelect={() => {
              fitToScreen({ width: window.innerWidth, height: window.innerHeight });
              onClose();
            }}
          >
            <Maximize className="size-4" />
            Fit to Screen
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
