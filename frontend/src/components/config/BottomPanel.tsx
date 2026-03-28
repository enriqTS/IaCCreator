'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import type { CanvasObject } from '@/types/diagram';
import { MIN_PANEL_HEIGHT, MAX_PANEL_HEIGHT_RATIO } from './panel-constants';
import TerraformTab from './TerraformTab';
import SchemaConfigForm from './SchemaConfigForm';
import VisualTab from './VisualTab';
import ZOrderControls from './ZOrderControls';
import GlobalTerraformConfigPanel from './GlobalTerraformConfigPanel';
import PillIndicator from './PillIndicator';

/** Determine available tabs for a given canvas object type. */
export function getTabsForObject(obj: CanvasObject): string[] {
  if (obj.objectType === 'architecture-block') {
    return ['Variables', 'Visual'];
  }
  return ['Visual'];
}

export default function BottomPanel() {
  const selectedObjectIds = useDiagramStore((s) => s.selectedObjectIds);
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);
  const removeCanvasObject = useDiagramStore((s) => s.removeCanvasObject);
  const groupSelectedObjects = useDiagramStore((s) => s.groupSelectedObjects);
  const ungroupObjects = useDiagramStore((s) => s.ungroupObjects);
  const bottomPanelExpanded = useDiagramStore((s) => s.bottomPanelExpanded);
  const bottomPanelHeight = useDiagramStore((s) => s.bottomPanelHeight);
  const toggleBottomPanel = useDiagramStore((s) => s.toggleBottomPanel);
  const setBottomPanelHeight = useDiagramStore((s) => s.setBottomPanelHeight);
  const setBottomPanelExpanded = useDiagramStore((s) => s.setBottomPanelExpanded);

  const selectedObjectId = selectedObjectIds.size === 1 ? Array.from(selectedObjectIds)[0] : null;
  const selectedObject = selectedObjectId ? canvasObjects.get(selectedObjectId) ?? null : null;
  const tabs = selectedObject ? getTabsForObject(selectedObject) : [];

  const [activeTab, setActiveTab] = useState<string>('');

  // --- Drag resize state (lifted to BottomPanel so it survives collapse) ---
  const isDragging = useRef(false);
  const isCollapsedDuringDrag = useRef(false);
  const dragStartY = useRef(0);
  const dragStartHeight = useRef(0);

  // Refs for latest store actions so stable listeners can call them
  const storeRef = useRef({ setBottomPanelHeight, setBottomPanelExpanded });
  storeRef.current = { setBottomPanelHeight, setBottomPanelExpanded };

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging.current) return;
    e.preventDefault();
    const delta = dragStartY.current - e.clientY;
    const rawHeight = dragStartHeight.current + delta;
    const maxHeight = MAX_PANEL_HEIGHT_RATIO * window.innerHeight;

    if (rawHeight < MIN_PANEL_HEIGHT) {
      if (!isCollapsedDuringDrag.current) {
        isCollapsedDuringDrag.current = true;
        storeRef.current.setBottomPanelExpanded(false);
      }
      return;
    }

    // Dragged back up after collapsing
    if (isCollapsedDuringDrag.current) {
      isCollapsedDuringDrag.current = false;
      const clamped = Math.min(Math.max(rawHeight, MIN_PANEL_HEIGHT), maxHeight);
      storeRef.current.setBottomPanelHeight(clamped);
      storeRef.current.setBottomPanelExpanded(true);
      return;
    }

    const clamped = Math.min(Math.max(rawHeight, MIN_PANEL_HEIGHT), maxHeight);
    storeRef.current.setBottomPanelHeight(clamped);
  }, []);

  const handleMouseUp = useCallback(() => {
    isDragging.current = false;
    isCollapsedDuringDrag.current = false;
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }, [handleMouseMove]);

  const handleResizeMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDragging.current = true;
    isCollapsedDuringDrag.current = false;
    dragStartY.current = e.clientY;
    const panel = (e.currentTarget as HTMLElement).closest('[data-testid="bottom-panel"]');
    dragStartHeight.current = panel ? panel.getBoundingClientRect().height : bottomPanelHeight;
    document.body.style.cursor = 'ns-resize';
    document.body.style.userSelect = 'none';
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, [handleMouseMove, handleMouseUp, bottomPanelHeight]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [handleMouseMove, handleMouseUp]);

  // Auto-expand/collapse panel based on selection state
  useEffect(() => {
    if (selectedObjectIds.size > 0) {
      setBottomPanelExpanded(true);
    } else {
      setBottomPanelExpanded(false);
    }
  }, [selectedObjectIds, setBottomPanelExpanded]);

  // Activate first available tab when selection changes
  useEffect(() => {
    if (tabs.length > 0) {
      setActiveTab(tabs[0]);
    } else {
      setActiveTab('Terraform');
    }
  }, [selectedObjectIds]); // eslint-disable-line react-hooks/exhaustive-deps

  // --- Inline resize handle (not a separate component, so it doesn't unmount) ---
  const resizeHandle = (
    <div
      data-testid="resize-handle"
      onMouseDown={handleResizeMouseDown}
      style={{
        height: 14,
        cursor: 'ns-resize',
        backgroundColor: 'transparent',
        position: 'relative',
        zIndex: 10,
        marginTop: -4,
      }}
    />
  );

  // --- Collapsed state ---
  if (!bottomPanelExpanded) {
    return (
      <div
        data-testid="bottom-panel"
        style={{
          position: 'fixed',
          bottom: 12,
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 50,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          padding: '8px 16px',
        }}
      >
        <PillIndicator expanded={false} onClick={toggleBottomPanel} />
      </div>
    );
  }

  // --- Expanded: Multi-selection ---
  if (selectedObjectIds.size > 1) {
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
        data-testid="bottom-panel"
        style={{
          position: 'fixed',
          bottom: 0, left: 0, right: 0,
          height: bottomPanelHeight,
          backgroundColor: '#1e1e1e',
          borderTop: '1px solid rgba(255, 255, 255, 0.1)',
          zIndex: 50,
          color: 'rgba(255, 255, 255, 0.9)',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 4 }}>
          <PillIndicator expanded={true} onClick={toggleBottomPanel} />
        </div>
        {resizeHandle}
        <div
          data-testid="multi-selection-summary"
          style={{
            padding: '16px 24px', fontSize: '14px',
            color: 'rgba(255, 255, 255, 0.7)',
            display: 'flex', alignItems: 'center', gap: '12px',
            flex: 1, overflowY: 'auto',
          }}
        >
          <span>{selectedObjectIds.size} objects selected</span>
          {showGroupButton && (
            <button data-testid="group-button" onClick={() => groupSelectedObjects()}
              style={{ padding: '4px 12px', fontSize: '12px', color: '#3b82f6', backgroundColor: 'transparent', border: '1px solid rgba(59, 130, 246, 0.4)', borderRadius: '4px', cursor: 'pointer' }}>
              Group
            </button>
          )}
          {showUngroupButton && (
            <button data-testid="ungroup-button" onClick={() => ungroupObjects(firstGroupId!)}
              style={{ padding: '4px 12px', fontSize: '12px', color: '#f59e0b', backgroundColor: 'transparent', border: '1px solid rgba(245, 158, 11, 0.4)', borderRadius: '4px', cursor: 'pointer' }}>
              Ungroup
            </button>
          )}
        </div>
      </div>
    );
  }

  // --- Expanded: No selection (global config) ---
  if (selectedObjectIds.size === 0) {
    return (
      <div
        data-testid="bottom-panel"
        style={{
          position: 'fixed',
          bottom: 0, left: 0, right: 0,
          height: bottomPanelHeight,
          backgroundColor: '#1e1e1e',
          borderTop: '1px solid rgba(255, 255, 255, 0.1)',
          zIndex: 50,
          color: 'rgba(255, 255, 255, 0.9)',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 4 }}>
          <PillIndicator expanded={true} onClick={toggleBottomPanel} />
        </div>
        {resizeHandle}
        <div data-testid="tab-bar" style={{ display: 'flex', alignItems: 'center', borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>
          <button data-testid="tab-terraform"
            style={{ padding: '10px 20px', fontSize: '13px', fontWeight: 600, color: '#fff', backgroundColor: '#2a2a2a', borderTop: 'none', borderLeft: 'none', borderRight: 'none', borderBottomStyle: 'solid', borderBottomWidth: '2px', borderBottomColor: '#3b82f6', cursor: 'pointer' }}>
            Terraform
          </button>
        </div>
        <div data-testid="tab-content" style={{ padding: '16px 24px', flex: 1, overflowY: 'auto' }}>
          <div data-testid="global-terraform-tab-content">
            <GlobalTerraformConfigPanel panelWidth={bottomPanelHeight} />
          </div>
        </div>
      </div>
    );
  }

  // --- Expanded: Single selection ---
  if (!selectedObject) return null;

  return (
    <div
      data-testid="bottom-panel"
      style={{
        position: 'fixed',
        bottom: 0, left: 0, right: 0,
        height: bottomPanelHeight,
        backgroundColor: '#1e1e1e',
        borderTop: '1px solid rgba(255, 255, 255, 0.1)',
        zIndex: 50,
        color: 'rgba(255, 255, 255, 0.9)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 4 }}>
        <PillIndicator expanded={true} onClick={toggleBottomPanel} />
      </div>
      {resizeHandle}
      <div data-testid="tab-bar" style={{ display: 'flex', alignItems: 'center', borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>
        {tabs.map((tab) => {
          const isActive = tab === activeTab;
          return (
            <button key={tab} data-testid={`tab-${tab.toLowerCase()}`} onClick={() => setActiveTab(tab)}
              style={{
                padding: '10px 20px', fontSize: '13px',
                fontWeight: isActive ? 600 : 400,
                color: isActive ? '#fff' : 'rgba(255, 255, 255, 0.5)',
                backgroundColor: isActive ? '#2a2a2a' : 'transparent',
                borderTop: 'none', borderLeft: 'none', borderRight: 'none',
                borderBottomStyle: 'solid', borderBottomWidth: '2px',
                borderBottomColor: isActive ? '#3b82f6' : 'transparent',
                cursor: 'pointer',
              }}>
              {tab}
            </button>
          );
        })}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '12px', marginRight: '12px' }}>
          {selectedObjectId && <ZOrderControls objectId={selectedObjectId} />}
          <button data-testid="delete-object-button"
            onClick={() => { if (selectedObjectId) removeCanvasObject(selectedObjectId); }}
            style={{ padding: '6px 12px', fontSize: '12px', color: '#ef4444', backgroundColor: 'transparent', border: '1px solid rgba(239, 68, 68, 0.4)', borderRadius: '4px', cursor: 'pointer' }}>
            🗑 Delete
          </button>
        </div>
      </div>
      <div data-testid="tab-content" style={{ padding: '16px 24px', flex: 1, overflowY: 'auto' }}>
        {activeTab === 'Terraform' && selectedObject?.objectType === 'architecture-block' && (
          <div data-testid="terraform-tab-content"><TerraformTab block={selectedObject} /></div>
        )}
        {activeTab === 'Variables' && selectedObject?.objectType === 'architecture-block' && (
          <div data-testid="variables-tab-content"><SchemaConfigForm elementId={selectedObject.id} serviceType={selectedObject.serviceType} /></div>
        )}
        {activeTab === 'Visual' && (
          <div data-testid="visual-tab-content"><VisualTab object={selectedObject} /></div>
        )}
      </div>
    </div>
  );
}
