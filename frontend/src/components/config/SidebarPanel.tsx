'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { useLayoutPreferencesStore } from '@/store/layout-preferences-store';
import type { CanvasObject, ArchitectureBlock } from '@/types/diagram';
import {
  MIN_SIDEBAR_WIDTH,
  MAX_SIDEBAR_WIDTH_RATIO,
} from './panel-constants';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { PanelLeftOpen, PanelRightOpen, PanelLeftClose, PanelRightClose, Trash2 } from 'lucide-react';
import GlobalTerraformConfigPanel from './GlobalTerraformConfigPanel';
import SchemaConfigForm from './schema/SchemaConfigForm';
import ApigwDynamicConfigUI from './apigw/ApigwDynamicConfigUI';
import VisualTab from './VisualTab';
import ConnectionConfigPanel from '@/connections/ConnectionConfigPanel';
import { findConnectorForLine, getSchemaForConnector } from '@/connections/connector-utils';
import { Label } from '@/components/ui/label';

/** Determine available tabs for a given canvas object type. */
export function getTabsForObject(obj: CanvasObject): string[] {
  if (obj.objectType === 'architecture-block') {
    return ['Variables', 'Visual'];
  }
  if (obj.objectType === 'line') {
    return ['Connection', 'Visual'];
  }
  return ['Visual'];
}

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
  const tabs = selectedObject ? getTabsForObject(selectedObject) : [];

  const [activeTab, setActiveTab] = useState<string>('');

  // Drag resize state
  const isDragging = useRef(false);
  const isCollapsedDuringDrag = useRef(false);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(0);
  const panelRef = useRef<HTMLDivElement>(null);

  // Keep latest store actions in a ref so stable listeners can call them
  const storeRef = useRef({ setSidebarWidth, setSidebarExpanded });
  storeRef.current = { setSidebarWidth, setSidebarExpanded };

  // Track dragging state for disabling transitions
  const isDraggingState = useRef(false);

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

  const handleMouseUp = useCallback(() => {
    isDragging.current = false;
    isDraggingState.current = false;
    isCollapsedDuringDrag.current = false;
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    // Force re-render to re-enable transitions
    if (panelRef.current) {
      panelRef.current.style.transition = '';
    }
  }, [handleMouseMove]);

  const handleResizeMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      isDragging.current = true;
      isDraggingState.current = true;
      isCollapsedDuringDrag.current = false;
      dragStartX.current = e.clientX;
      dragStartWidth.current = sidebarWidth;
      document.body.style.cursor = 'ew-resize';
      document.body.style.userSelect = 'none';
      // Disable transitions during drag
      if (panelRef.current) {
        panelRef.current.style.transition = 'none';
      }
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    },
    [handleMouseMove, handleMouseUp, sidebarWidth],
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [handleMouseMove, handleMouseUp]);

  // Auto-expand/collapse sidebar based on selection state
  useEffect(() => {
    if (selectedObjectIds.size > 0) {
      setSidebarExpanded(true);
    } else {
      setSidebarExpanded(false);
    }
  }, [selectedObjectIds, setSidebarExpanded]);

  // Activate first available tab when selection changes
  useEffect(() => {
    if (tabs.length > 0) {
      setActiveTab(tabs[0]);
    }
  }, [selectedObjectIds]); // eslint-disable-line react-hooks/exhaustive-deps

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
        transition: isDraggingState.current ? 'none' : undefined,
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

        {/* Single selection: tabbed config view */}
        {selectedObjectIds.size === 1 && selectedObject && (
          <SingleSelectionView
            selectedObject={selectedObject}
            selectedObjectId={selectedObjectId!}
            tabs={tabs}
            activeTab={activeTab}
            setActiveTab={setActiveTab}
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
  const removeCanvasObject = useDiagramStore((s) => s.removeCanvasObject);
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

/** Single selection: tab bar with Variables/Visual tabs, Z-order controls, Delete button */
function SingleSelectionView({
  selectedObject,
  selectedObjectId,
  tabs,
  activeTab,
  setActiveTab,
}: {
  selectedObject: CanvasObject;
  selectedObjectId: string;
  tabs: string[];
  activeTab: string;
  setActiveTab: (tab: string) => void;
}) {
  const removeCanvasObject = useDiagramStore((s) => s.removeCanvasObject);
  const connectors = useDiagramStore((s) => s.connectors);
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);
  // Ensure activeTab is valid for current tabs
  const effectiveTab = tabs.includes(activeTab) ? activeTab : tabs[0] ?? '';

  // Resolve connector and schema for line objects
  const lineConnectorData = (() => {
    if (selectedObject.objectType !== 'line') return null;
    const connector = findConnectorForLine(selectedObject, connectors, canvasObjects);
    if (!connector) return { connector: null, schema: null, sourceBlock: null, targetBlock: null };
    const schema = getSchemaForConnector(connector, canvasObjects);
    const sourceBlock = canvasObjects.get(connector.sourceId) as ArchitectureBlock | undefined;
    const targetBlock = canvasObjects.get(connector.targetId) as ArchitectureBlock | undefined;
    return { connector, schema, sourceBlock: sourceBlock ?? null, targetBlock: targetBlock ?? null };
  })();

  return (
    <div className="flex flex-col gap-3">
      <Tabs value={effectiveTab} onValueChange={setActiveTab}>
        <div className="flex items-center gap-2">
          <TabsList data-testid="tab-bar" className="flex-1">
            {tabs.map((tab) => (
              <TabsTrigger
                key={tab}
                value={tab}
                data-testid={`tab-${tab.toLowerCase()}`}
              >
                {tab}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>

        {/* Tab content */}
        {tabs.includes('Variables') && (
          <TabsContent value="Variables" data-testid="variables-tab-content">
            {selectedObject.objectType === 'architecture-block' && (
              selectedObject.serviceType === 'api-gateway'
                ? <ApigwDynamicConfigUI elementId={selectedObjectId} />
                : <SchemaConfigForm elementId={selectedObjectId} serviceType={selectedObject.serviceType} />
            )}
          </TabsContent>
        )}
        {tabs.includes('Connection') && (
          <TabsContent value="Connection" data-testid="connection-tab-content">
            <ConnectionTabContent lineConnectorData={lineConnectorData} />
          </TabsContent>
        )}
        <TabsContent value="Visual" data-testid="visual-tab-content">
          <VisualTab object={selectedObject} />
        </TabsContent>
      </Tabs>
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

/** Renders the Connection tab content for a selected line object */
function ConnectionTabContent({
  lineConnectorData,
}: {
  lineConnectorData: {
    connector: import('@/types/diagram').Connector | null;
    schema: import('@/connections').ConnectionSchema | null;
    sourceBlock: ArchitectureBlock | null;
    targetBlock: ArchitectureBlock | null;
  } | null;
}) {
  // No connector found — line is a standalone drawing line
  if (!lineConnectorData || !lineConnectorData.connector) {
    return (
      <div data-testid="connection-no-connector" className="flex flex-col gap-2 py-2">
        <Label className="text-sm text-muted-foreground">
          This line is not connected to any services.
        </Label>
      </div>
    );
  }

  const { connector, schema, sourceBlock, targetBlock } = lineConnectorData;

  // Connector exists but no schema for this service pair
  if (!schema || !sourceBlock || !targetBlock) {
    return (
      <div data-testid="connection-no-schema" className="flex flex-col gap-2 py-2">
        {sourceBlock && targetBlock && (
          <div className="flex items-center gap-2">
            <Label className="text-sm font-semibold text-foreground">
              {sourceBlock.name}
            </Label>
            <span className="text-muted-foreground text-sm">→</span>
            <Label className="text-sm font-semibold text-foreground">
              {targetBlock.name}
            </Label>
          </div>
        )}
        <span className="text-xs text-muted-foreground">
          No additional configuration available for this connection type.
        </span>
      </div>
    );
  }

  // Full connection config panel
  return (
    <ConnectionConfigPanel
      connector={connector}
      sourceBlock={sourceBlock}
      targetBlock={targetBlock}
      schema={schema}
    />
  );
}
