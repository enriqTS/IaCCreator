'use client';

import { useEffect, useRef, useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { useLayoutPreferencesStore } from '@/store/layout-preferences-store';
import type { CanvasObject } from '@/types/diagram';
import {
  MIN_SIDEBAR_WIDTH,
  MAX_SIDEBAR_WIDTH_RATIO,
} from './panel-constants';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { PanelLeftOpen, PanelRightOpen, PanelLeftClose, PanelRightClose, Trash2 } from 'lucide-react';
import GlobalTerraformConfigPanel from './GlobalTerraformConfigPanel';
import VisualTab from './visual/VisualTab';

export default function SidebarPanel() {
  const sidebarExpanded = useDiagramStore((s) => s.sidebarExpanded);
  const sidebarWidth = useDiagramStore((s) => s.sidebarWidth);
  const setSidebarWidth = useDiagramStore((s) => s.setSidebarWidth);
  const setSidebarExpanded = useDiagramStore((s) => s.setSidebarExpanded);
  const selectedObjectIds = useDiagramStore((s) => s.selectedObjectIds);
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);
  const groupSelectedObjects = useDiagramStore((s) => s.groupSelectedObjects);
  const ungroupObjects = useDiagramStore((s) => s.ungroupObjects);
  const sidebarSide = useLayoutPreferencesStore((s) => s.sidebarSide);

  // Derive selection state
  const selectedObjectId = selectedObjectIds.size === 1 ? Array.from(selectedObjectIds)[0] : null;
  const selectedObject = selectedObjectId ? canvasObjects.get(selectedObjectId) ?? null : null;

  // Drag resize state
  const isDragging = useRef(false);
  const isCollapsedDuringDrag = useRef(false);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(0);
  const panelRef = useRef<HTMLDivElement>(null);

  // Keep latest store actions in a ref so stable listeners can call them
  const storeRef = useRef({ setSidebarWidth, setSidebarExpanded });
  useEffect(() => {
    storeRef.current = { setSidebarWidth, setSidebarExpanded };
  });

  // Track dragging state for disabling transitions

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDragging.current) return;
      e.preventDefault();

      const deltaX = e.clientX - dragStartX.current;
      // When sidebar is on the left, dragging the right-edge handle to the right increases width
      // When sidebar is on the right, dragging the left-edge handle to the left increases width
      const sidebarSideVal = useLayoutPreferencesStore.getState().sidebarSide;
      const rawWidth =
        sidebarSideVal === 'left'
          ? dragStartWidth.current + deltaX
          : dragStartWidth.current - deltaX;

      const maxWidth = MAX_SIDEBAR_WIDTH_RATIO * window.innerWidth;

      if (rawWidth < MIN_SIDEBAR_WIDTH) {
        if (!isCollapsedDuringDrag.current) {
          isCollapsedDuringDrag.current = true;
          storeRef.current.setSidebarExpanded(false);
        }
        return;
      }

      // Dragged back after collapsing
      if (isCollapsedDuringDrag.current) {
        isCollapsedDuringDrag.current = false;
        const clamped = Math.min(Math.max(rawWidth, MIN_SIDEBAR_WIDTH), maxWidth);
        storeRef.current.setSidebarWidth(clamped);
        storeRef.current.setSidebarExpanded(true);
        return;
      }

      const clamped = Math.min(Math.max(rawWidth, MIN_SIDEBAR_WIDTH), maxWidth);
      storeRef.current.setSidebarWidth(clamped);
    },
    [],
  );

  // One controller drops both document listeners, so neither handler references the other
  const dragListeners = useRef<AbortController | null>(null);

  const endDrag = useCallback(() => {
    isDragging.current = false;
    isCollapsedDuringDrag.current = false;
    dragListeners.current?.abort();
    dragListeners.current = null;
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    // Re-enable transitions now the drag is over
    if (panelRef.current) {
      panelRef.current.style.transition = '';
    }
  }, []);

  const handleResizeMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      isDragging.current = true;
      isCollapsedDuringDrag.current = false;
      dragStartX.current = e.clientX;
      dragStartWidth.current = sidebarWidth;
      document.body.style.cursor = 'ew-resize';
      document.body.style.userSelect = 'none';
      // Disable transitions during drag
      if (panelRef.current) {
        panelRef.current.style.transition = 'none';
      }
      dragListeners.current?.abort();
      const controller = new AbortController();
      dragListeners.current = controller;
      document.addEventListener('mousemove', handleMouseMove, { signal: controller.signal });
      document.addEventListener('mouseup', endDrag, { signal: controller.signal });
    },
    [handleMouseMove, endDrag, sidebarWidth],
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      dragListeners.current?.abort();
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, []);

  // Auto-expand/collapse sidebar based on selection state
  useEffect(() => {
    if (selectedObjectIds.size > 0) {
      setSidebarExpanded(true);
    } else {
      setSidebarExpanded(false);
    }
  }, [selectedObjectIds, setSidebarExpanded]);

  const isLeft = sidebarSide === 'left';

  // When collapsed, render only the toggle indicator on the configured side edge
  if (!sidebarExpanded) {
    return (
      <div
        data-testid="sidebar-toggle-collapsed"
        className={cn(
          'fixed top-1/2 z-50 -translate-y-1/2',
          isLeft ? 'left-0' : 'right-0',
        )}
      >
        <Button
          variant="outline"
          size="icon"
          data-testid="sidebar-expand-button"
          onClick={() => setSidebarExpanded(true)}
          className={cn(
            'shadow-md',
            isLeft ? 'rounded-l-none border-l-0' : 'rounded-r-none border-r-0',
          )}
          aria-label="Expand sidebar"
        >
          {isLeft ? <PanelLeftOpen className="size-5" /> : <PanelRightOpen className="size-5" />}
        </Button>
      </div>
    );
  }

  return (
    <div
      ref={panelRef}
      data-testid="sidebar-panel"
      data-side={sidebarSide}
      className={cn(
        'fixed inset-y-0 z-50 flex flex-col bg-background shadow-lg',
        isLeft ? 'left-0 border-r' : 'right-0 border-l',
      )}
      style={{
        width: sidebarWidth,
      }}
    >
      {/* Resize handle on the inner edge */}
      <div
        data-testid="sidebar-resize-handle"
        onMouseDown={handleResizeMouseDown}
        className={cn(
          'absolute inset-y-0 z-10 w-2 cursor-ew-resize',
          'hover:bg-primary/20 active:bg-primary/30',
          'transition-colors',
          isLeft ? 'right-0' : 'left-0',
        )}
      />

      {/* Header with collapse toggle */}
      <div className="flex items-center justify-between border-b px-3 py-2">
        <span className="text-sm font-medium">Configuration</span>
        <Button
          variant="ghost"
          size="icon-sm"
          data-testid="sidebar-collapse-button"
          onClick={() => setSidebarExpanded(false)}
          aria-label="Collapse sidebar"
        >
          {isLeft ? <PanelLeftClose className="size-4" /> : <PanelRightClose className="size-4" />}
        </Button>
      </div>

      {/* Content area */}
      <div
        data-testid="sidebar-content"
        className="flex-1 overflow-y-auto p-4"
      >
        {/* No selection: Global Terraform Config */}
        {selectedObjectIds.size === 0 && (
          <div data-testid="global-terraform-tab-content">
            <GlobalTerraformConfigPanel panelWidth={sidebarWidth} />
          </div>
        )}

        {/* Multi-selection: count + Group/Ungroup buttons */}
        {selectedObjectIds.size > 1 && (
          <MultiSelectionView
            selectedObjectIds={selectedObjectIds}
            canvasObjects={canvasObjects}
            groupSelectedObjects={groupSelectedObjects}
            ungroupObjects={ungroupObjects}
          />
        )}

        {/* Single selection: visual config; everything else lives in the overlay */}
        {selectedObjectIds.size === 1 && selectedObject && (
          <SingleSelectionView
            selectedObject={selectedObject}
            selectedObjectId={selectedObjectId!}
          />
        )}
      </div>
    </div>
  );
}

/** Multi-selection summary with Group/Ungroup buttons */
function MultiSelectionView({
  selectedObjectIds,
  canvasObjects,
  groupSelectedObjects,
  ungroupObjects,
}: {
  selectedObjectIds: Set<string>;
  canvasObjects: Map<string, CanvasObject>;
  groupSelectedObjects: () => string | null;
  ungroupObjects: (groupId: string) => void;
}) {
  const selectedObjects = Array.from(selectedObjectIds)
    .map((id) => canvasObjects.get(id))
    .filter(Boolean) as CanvasObject[];
  const groupIds = new Set(selectedObjects.map((obj) => obj.groupId).filter(Boolean));
  const allInSameGroup =
    groupIds.size === 1 &&
    selectedObjects.every((obj) => obj.groupId === selectedObjects[0].groupId) &&
    selectedObjects[0].groupId !== undefined;
  const showGroupButton = !allInSameGroup;
  const firstGroupId = selectedObjects.find((obj) => obj.groupId)?.groupId ?? null;
  const showUngroupButton = firstGroupId !== null;

  return (
    <div
      data-testid="multi-selection-summary"
      className="flex flex-col gap-3"
    >
      <span className="text-sm text-muted-foreground">
        {selectedObjectIds.size} objects selected
      </span>
      <div className="flex items-center gap-2">
        {showGroupButton && (
          <Button
            variant="outline"
            size="sm"
            data-testid="group-button"
            onClick={() => groupSelectedObjects()}
          >
            Group
          </Button>
        )}
        {showUngroupButton && (
          <Button
            variant="outline"
            size="sm"
            data-testid="ungroup-button"
            onClick={() => ungroupObjects(firstGroupId!)}
          >
            Ungroup
          </Button>
        )}
      </div>
      <Button
        variant="destructive"
        size="sm"
        data-testid="delete-object-button"
        onClick={() => { useDiagramStore.getState().removeMultipleCanvasObjects(selectedObjectIds); }}
        className="w-full"
      >
        <Trash2 className="size-4" /> Delete ({selectedObjectIds.size})
      </Button>
    </div>
  );
}

/** Single selection: visual configuration and the delete action. */
function SingleSelectionView({
  selectedObject,
  selectedObjectId,
}: {
  selectedObject: CanvasObject;
  selectedObjectId: string;
}) {
  const removeCanvasObject = useDiagramStore((s) => s.removeCanvasObject);

  return (
    <div className="flex flex-col gap-3">
      <div data-testid="visual-tab-content">
        <VisualTab object={selectedObject} />
      </div>
      <Button
        variant="destructive"
        size="sm"
        data-testid="delete-object-button"
        onClick={() => removeCanvasObject(selectedObjectId)}
        className="w-full"
      >
        <Trash2 className="size-4" /> Delete
      </Button>
    </div>
  );
}
