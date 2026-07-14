'use client';

import { useEffect, useRef } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import {
  ArrowUpToLine,
  ArrowUp,
  ArrowDown,
  ArrowDownToLine,
  Copy,
  Clipboard,
  Lock,
  Unlock,
  Pencil,
  Group,
  Ungroup,
  Cable,
  Settings,
  Trash2,
} from 'lucide-react';

interface CanvasObjectContextMenuProps {
  menu: { objectId: string; x: number; y: number };
  onClose: () => void;
  onRename?: (objectId: string) => void;
}

export default function CanvasObjectContextMenu({ menu, onClose, onRename }: CanvasObjectContextMenuProps) {
  const bringToFront = useDiagramStore((s) => s.bringToFront);
  const sendToBack = useDiagramStore((s) => s.sendToBack);
  const bringForward = useDiagramStore((s) => s.bringForward);
  const sendBackward = useDiagramStore((s) => s.sendBackward);
  const removeCanvasObject = useDiagramStore((s) => s.removeCanvasObject);
  const duplicateSelectedObjects = useDiagramStore((s) => s.duplicateSelectedObjects);
  const copySelectedObjects = useDiagramStore((s) => s.copySelectedObjects);
  const toggleLockObjects = useDiagramStore((s) => s.toggleLockObjects);
  const groupSelectedObjects = useDiagramStore((s) => s.groupSelectedObjects);
  const ungroupObjects = useDiagramStore((s) => s.ungroupObjects);
  const selectedObjectIds = useDiagramStore((s) => s.selectedObjectIds);
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);

  const menuRef = useRef<HTMLDivElement>(null);

  const isSingleSelection = selectedObjectIds.size === 1;
  const allLocked = selectedObjectIds.size > 0 && Array.from(selectedObjectIds).every((id) => canvasObjects.get(id)?.locked);

  const groupIdsInSelection = new Set<string>();
  for (const id of selectedObjectIds) {
    const obj = canvasObjects.get(id);
    if (obj?.groupId) groupIdsInSelection.add(obj.groupId);
  }
  const hasGroupedObjects = groupIdsInSelection.size > 0;
  const canGroup = selectedObjectIds.size >= 2 && !hasGroupedObjects;

  const singleObject = isSingleSelection ? canvasObjects.get(menu.objectId) : null;
  const objectType = singleObject?.objectType;
  const showEditConnection = isSingleSelection && objectType === 'line';
  const showConfigureService = isSingleSelection && objectType === 'architecture-block';

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) onClose();
    }
    // Use capture phase so we catch the event before stopPropagation in canvas handlers
    document.addEventListener('pointerdown', handleClickOutside, true);
    return () => document.removeEventListener('pointerdown', handleClickOutside, true);
  }, [onClose]);

  useEffect(() => {
    function handleEscape(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  const itemClass = 'flex items-center gap-2 px-3 py-1.5 text-sm rounded-sm cursor-default select-none hover:bg-accent hover:text-accent-foreground outline-none';
  const destructiveClass = 'flex items-center gap-2 px-3 py-1.5 text-sm rounded-sm cursor-default select-none text-destructive hover:bg-destructive/10 hover:text-destructive outline-none';
  const disabledClass = 'opacity-50 pointer-events-none';
  const separatorClass = '-mx-1 my-1 h-px bg-border';

  function Item({ onClick, children, disabled, destructive }: { onClick: () => void; children: React.ReactNode; disabled?: boolean; destructive?: boolean }) {
    return (
      <div
        role="menuitem"
        tabIndex={-1}
        className={`${destructive ? destructiveClass : itemClass} ${disabled ? disabledClass : ''}`}
        onClick={disabled ? undefined : onClick}
      >
        {children}
      </div>
    );
  }

  return (
    <div
      ref={menuRef}
      data-testid="canvas-context-menu"
      role="menu"
      style={{ position: 'fixed', top: menu.y, left: menu.x, zIndex: 9999 }}
      className="min-w-[180px] rounded-md border bg-popover p-1 text-popover-foreground shadow-md"
    >
      {/* Layering */}
      <Item onClick={() => { bringToFront(menu.objectId); onClose(); }}>
        <ArrowUpToLine className="size-4" /> Bring to Front
      </Item>
      <Item onClick={() => { bringForward(menu.objectId); onClose(); }}>
        <ArrowUp className="size-4" /> Bring Forward
      </Item>
      <Item onClick={() => { sendBackward(menu.objectId); onClose(); }}>
        <ArrowDown className="size-4" /> Send Backward
      </Item>
      <Item onClick={() => { sendToBack(menu.objectId); onClose(); }}>
        <ArrowDownToLine className="size-4" /> Send to Back
      </Item>

      <div className={separatorClass} />

      {/* Edit */}
      <Item onClick={() => { duplicateSelectedObjects(); onClose(); }}>
        <Copy className="size-4" /> Duplicate
      </Item>
      <Item onClick={() => { copySelectedObjects(); onClose(); }}>
        <Clipboard className="size-4" /> Copy
      </Item>

      <div className={separatorClass} />

      {/* Object management */}
      <Item onClick={() => { toggleLockObjects(selectedObjectIds); onClose(); }}>
        {allLocked ? <Unlock className="size-4" /> : <Lock className="size-4" />}
        {allLocked ? 'Unlock' : 'Lock'}
      </Item>
      {isSingleSelection && (
        <Item onClick={() => { onRename?.(menu.objectId); }}>
          <Pencil className="size-4" /> Rename
        </Item>
      )}

      {/* Grouping */}
      {(canGroup || hasGroupedObjects) && <div className={separatorClass} />}
      {canGroup && (
        <Item onClick={() => { groupSelectedObjects(); onClose(); }}>
          <Group className="size-4" /> Group
        </Item>
      )}
      {hasGroupedObjects && (
        <Item onClick={() => { for (const gid of groupIdsInSelection) ungroupObjects(gid); onClose(); }}>
          <Ungroup className="size-4" /> Ungroup
        </Item>
      )}

      {/* Type-specific */}
      {(showEditConnection || showConfigureService) && <div className={separatorClass} />}
      {showEditConnection && (
        <Item onClick={() => { useDiagramStore.getState().setSidebarExpanded(true); onClose(); }}>
          <Cable className="size-4" /> Edit Connection
        </Item>
      )}
      {showConfigureService && (
        <Item onClick={() => { useDiagramStore.getState().setSidebarExpanded(true); onClose(); }}>
          <Settings className="size-4" /> Configure Service
        </Item>
      )}

      <div className={separatorClass} />

      {/* Delete */}
      <Item destructive onClick={() => { useDiagramStore.getState().removeMultipleCanvasObjects(selectedObjectIds); onClose(); }}>
        <Trash2 className="size-4" /> Delete
      </Item>
    </div>
  );
}
