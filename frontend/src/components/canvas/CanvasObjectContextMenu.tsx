'use client';

import { useEffect, useRef } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import {
  ArrowUpToLine,
  ArrowUp,
  ArrowDown,
  ArrowDownToLine,
  Trash2,
} from 'lucide-react';

export interface ContextMenuState {
  objectId: string;
  x: number;
  y: number;
}

interface CanvasObjectContextMenuProps {
  menu: ContextMenuState;
  onClose: () => void;
}

export default function CanvasObjectContextMenu({ menu, onClose }: CanvasObjectContextMenuProps) {
  const bringToFront = useDiagramStore((s) => s.bringToFront);
  const sendToBack = useDiagramStore((s) => s.sendToBack);
  const bringForward = useDiagramStore((s) => s.bringForward);
  const sendBackward = useDiagramStore((s) => s.sendBackward);
  const removeCanvasObject = useDiagramStore((s) => s.removeCanvasObject);

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

  return (
    <div
      ref={menuRef}
      data-testid="canvas-context-menu"
      style={{
        position: 'fixed',
        top: menu.y,
        left: menu.x,
        zIndex: 100,
      }}
    >
      <DropdownMenu open onOpenChange={(open) => { if (!open) onClose(); }}>
        <DropdownMenuContent align="start" side="bottom" sideOffset={0}>
          <DropdownMenuItem onSelect={() => { bringToFront(menu.objectId); onClose(); }}>
            <ArrowUpToLine className="size-4" />
            Bring to Front
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => { bringForward(menu.objectId); onClose(); }}>
            <ArrowUp className="size-4" />
            Bring Forward
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => { sendBackward(menu.objectId); onClose(); }}>
            <ArrowDown className="size-4" />
            Send Backward
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => { sendToBack(menu.objectId); onClose(); }}>
            <ArrowDownToLine className="size-4" />
            Send to Back
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            variant="destructive"
            onSelect={() => { removeCanvasObject(menu.objectId); onClose(); }}
          >
            <Trash2 className="size-4" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
