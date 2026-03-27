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

  // Derive state for conditional menu items
  const isSingleSelection = selectedObjectIds.size === 1;

  // Check if ALL selected objects are locked
  const allLocked = selectedObjectIds.size > 0 && Array.from(selectedObjectIds).every((id) => {
    const obj = canvasObjects.get(id);
    return obj?.locked;
  });

  // Check if any selected object has a groupId (for Ungroup)
  const groupIdsInSelection = new Set<string>();
  for (const id of selectedObjectIds) {
    const obj = canvasObjects.get(id);
    if (obj?.groupId) {
      groupIdsInSelection.add(obj.groupId);
    }
  }
  const hasGroupedObjects = groupIdsInSelection.size > 0;

  // Check if Group should be shown: >=2 selected AND none have a groupId
  const canGroup = selectedObjectIds.size >= 2 && !hasGroupedObjects;

  // Determine object type for type-specific items (single selection only)
  const singleObject = isSingleSelection ? canvasObjects.get(menu.objectId) : null;
  const objectType = singleObject?.objectType;
  const showEditConnection = isSingleSelection && objectType === 'line';
  const showConfigureService = isSingleSelection && objectType === 'architecture-block';
  const showTypeSpecific = showEditConnection || showConfigureService;

  // Show grouping separator/items only if group or ungroup is visible
  const showGroupingSection = canGroup || hasGroupedObjects;

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
          {/* Group 1 - Layering */}
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

          {/* Group 2 - Edit */}
          <DropdownMenuItem onSelect={() => { duplicateSelectedObjects(); onClose(); }}>
            <Copy className="size-4" />
            Duplicate
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => { copySelectedObjects(); onClose(); }}>
            <Clipboard className="size-4" />
            Copy
          </DropdownMenuItem>

          <DropdownMenuSeparator />

          {/* Group 3 - Object management */}
          <DropdownMenuItem onSelect={() => { toggleLockObjects(selectedObjectIds); onClose(); }}>
            {allLocked ? <Unlock className="size-4" /> : <Lock className="size-4" />}
            {allLocked ? 'Unlock' : 'Lock'}
          </DropdownMenuItem>
          {isSingleSelection && (
            <DropdownMenuItem onSelect={() => { onRename?.(menu.objectId); }}>
              <Pencil className="size-4" />
              Rename
            </DropdownMenuItem>
          )}

          {/* Separator before grouping (only if group/ungroup items shown) */}
          {showGroupingSection && <DropdownMenuSeparator />}

          {/* Group 4 - Grouping (conditional) */}
          {canGroup && (
            <DropdownMenuItem onSelect={() => { groupSelectedObjects(); onClose(); }}>
              <Group className="size-4" />
              Group
            </DropdownMenuItem>
          )}
          {hasGroupedObjects && (
            <DropdownMenuItem onSelect={() => {
              for (const gid of groupIdsInSelection) {
                ungroupObjects(gid);
              }
              onClose();
            }}>
              <Ungroup className="size-4" />
              Ungroup
            </DropdownMenuItem>
          )}

          {/* Separator before type-specific (only if type-specific items shown) */}
          {showTypeSpecific && <DropdownMenuSeparator />}

          {/* Group 5 - Type-specific (conditional, single selection only) */}
          {showEditConnection && (
            <DropdownMenuItem onSelect={() => {
              useDiagramStore.getState().setSidebarExpanded(true);
              onClose();
            }}>
              <Cable className="size-4" />
              Edit Connection
            </DropdownMenuItem>
          )}
          {showConfigureService && (
            <DropdownMenuItem onSelect={() => {
              useDiagramStore.getState().setSidebarExpanded(true);
              onClose();
            }}>
              <Settings className="size-4" />
              Configure Service
            </DropdownMenuItem>
          )}

          <DropdownMenuSeparator />

          {/* Group 6 - Destructive */}
          <DropdownMenuItem
            variant="destructive"
            onSelect={() => {
              for (const id of selectedObjectIds) {
                removeCanvasObject(id);
              }
              onClose();
            }}
          >
            <Trash2 className="size-4" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
