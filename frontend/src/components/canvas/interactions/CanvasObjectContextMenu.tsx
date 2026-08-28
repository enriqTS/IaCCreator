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
  PanelsTopLeft,
  Box,
  BoxSelect,
  LogOut,
  LayoutGrid,
} from 'lucide-react';
import { useEditorDomainStore } from '@/store/editor-domain-store';
import { isSemanticContainer, semanticType } from '@/utils/semantic-containment';

interface CanvasObjectContextMenuProps {
  menu: { objectId: string; x: number; y: number };
  onClose: () => void;
  onRename?: (objectId: string) => void;
}

const itemClass = 'flex items-center gap-2 px-3 py-1.5 text-sm rounded-sm cursor-default select-none hover:bg-accent hover:text-accent-foreground outline-none';
const destructiveClass = 'flex items-center gap-2 px-3 py-1.5 text-sm rounded-sm cursor-default select-none text-destructive hover:bg-destructive/10 hover:text-destructive outline-none';
const disabledClass = 'opacity-50 pointer-events-none';
const separatorClass = '-mx-1 my-1 h-px bg-border';

// Declared at module scope so it is not recreated, and remounted, on every render
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

export default function CanvasObjectContextMenu({ menu, onClose, onRename }: CanvasObjectContextMenuProps) {
  const bringToFront = useDiagramStore((s) => s.bringToFront);
  const sendToBack = useDiagramStore((s) => s.sendToBack);
  const bringForward = useDiagramStore((s) => s.bringForward);
  const sendBackward = useDiagramStore((s) => s.sendBackward);
  const duplicateSelectedObjects = useDiagramStore((s) => s.duplicateSelectedObjects);
  const copySelectedObjects = useDiagramStore((s) => s.copySelectedObjects);
  const toggleLockObjects = useDiagramStore((s) => s.toggleLockObjects);
  const groupSelectedObjects = useDiagramStore((s) => s.groupSelectedObjects);
  const ungroupObjects = useDiagramStore((s) => s.ungroupObjects);
  const selectedObjectIds = useDiagramStore((s) => s.selectedObjectIds);
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);
  const containmentRules = useEditorDomainStore((s) => s.containmentRules);

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
  const showPresentation = singleObject?.objectType === 'architecture-block'
    && (singleObject.serviceType === 'vpc' || singleObject.serviceType === 'subnet');
  const parentId = singleObject && 'parentContainerId' in singleObject
    ? singleObject.parentContainerId
    : undefined;
  const descendantIds = new Set<string>();
  if (singleObject) {
    const queue = [singleObject.id];
    while (queue.length > 0) {
      const current = queue.pop()!;
      for (const candidate of canvasObjects.values()) {
        if ('parentContainerId' in candidate && candidate.parentContainerId === current && !descendantIds.has(candidate.id)) {
          descendantIds.add(candidate.id);
          queue.push(candidate.id);
        }
      }
    }
  }
  const eligibleContainers = singleObject
    ? [...canvasObjects.values()].filter((candidate) =>
        candidate.id !== singleObject.id
        && candidate.id !== parentId
        && !descendantIds.has(candidate.id)
        && isSemanticContainer(candidate)
        && containmentRules.some((rule) => rule.child_type === semanticType(singleObject)
          && rule.parent_type === semanticType(candidate)))
    : [];

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
      {(showEditConnection || showConfigureService || showPresentation) && <div className={separatorClass} />}
      {showEditConnection && (
        <Item onClick={() => { useDiagramStore.getState().openConfigOverlay(menu.objectId); onClose(); }}>
          <Cable className="size-4" /> Edit Connection
        </Item>
      )}
      {showConfigureService && (
        <Item onClick={() => { useDiagramStore.getState().openConfigOverlay(menu.objectId); onClose(); }}>
          <Settings className="size-4" /> Configure Service
        </Item>
      )}
      {isSingleSelection && eligibleContainers.map((container) => (
        <Item key={container.id} onClick={() => {
          void useDiagramStore.getState().assignSemanticParent(menu.objectId, container.id);
          onClose();
        }}>
          <Box className="size-4" /> Move into {container.name}
        </Item>
      ))}
      {isSingleSelection && parentId && (
        <>
          <Item onClick={() => {
            void useDiagramStore.getState().assignSemanticParent(menu.objectId, null);
            onClose();
          }}>
            <LogOut className="size-4" /> Remove from Container
          </Item>
          <Item onClick={() => { useDiagramStore.getState().selectObject(parentId); onClose(); }}>
            <BoxSelect className="size-4" /> Select Container
          </Item>
        </>
      )}
      {isSingleSelection && singleObject && isSemanticContainer(singleObject) && (
        <Item onClick={() => {
          useDiagramStore.getState().layoutSemanticContainer(singleObject.id);
          onClose();
        }}>
          <LayoutGrid className="size-4" /> Arrange Contents
        </Item>
      )}
      {showPresentation && singleObject && singleObject.objectType === 'architecture-block' && (
        <Item onClick={() => {
          void useDiagramStore.getState().setResourcePresentation(
            menu.objectId,
            singleObject.presentation === 'container' ? 'node' : 'container',
          );
          onClose();
        }}>
          <PanelsTopLeft className="size-4" />
          {singleObject.presentation === 'container' ? 'Show as Node' : 'Show as Container'}
        </Item>
      )}

      <div className={separatorClass} />

      {/* Delete */}
      {isSingleSelection && singleObject && isSemanticContainer(singleObject) && descendantIds.size > 0 ? (
        <>
          <Item destructive onClick={() => { useDiagramStore.getState().removeCanvasObject(singleObject.id); onClose(); }}>
            <Trash2 className="size-4" /> Delete and Reparent Contents
          </Item>
          <Item destructive onClick={() => {
            useDiagramStore.getState().removeMultipleCanvasObjects(new Set([singleObject.id, ...descendantIds]));
            onClose();
          }}>
            <Trash2 className="size-4" /> Delete Subtree
          </Item>
        </>
      ) : (
        <Item destructive onClick={() => { useDiagramStore.getState().removeMultipleCanvasObjects(selectedObjectIds); onClose(); }}>
          <Trash2 className="size-4" /> Delete
        </Item>
      )}
    </div>
  );
}
