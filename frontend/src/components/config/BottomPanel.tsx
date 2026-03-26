'use client';

import { useState, useEffect } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import type { CanvasObject } from '@/types/diagram';
import TerraformTab from './TerraformTab';
import VisualTab from './VisualTab';
import ZOrderControls from './ZOrderControls';

/** Determine available tabs for a given canvas object type. */
export function getTabsForObject(obj: CanvasObject): string[] {
  if (obj.objectType === 'architecture-block') {
    return ['Terraform', 'Visual'];
  }
  return ['Visual'];
}

export default function BottomPanel() {
  const selectedObjectIds = useDiagramStore((s) => s.selectedObjectIds);
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);
  const removeCanvasObject = useDiagramStore((s) => s.removeCanvasObject);
  const groupSelectedObjects = useDiagramStore((s) => s.groupSelectedObjects);
  const ungroupObjects = useDiagramStore((s) => s.ungroupObjects);

  // Get the single selected object (only when exactly one is selected)
  const selectedObjectId = selectedObjectIds.size === 1 ? Array.from(selectedObjectIds)[0] : null;
  const selectedObject = selectedObjectId ? canvasObjects.get(selectedObjectId) ?? null : null;
  const tabs = selectedObject ? getTabsForObject(selectedObject) : [];

  const [activeTab, setActiveTab] = useState<string>('');

  // Activate first available tab when selection changes
  useEffect(() => {
    if (tabs.length > 0) {
      setActiveTab(tabs[0]);
    } else {
      setActiveTab('');
    }
  }, [selectedObjectIds]); // eslint-disable-line react-hooks/exhaustive-deps

  // Close panel when no objects are selected
  if (selectedObjectIds.size === 0) return null;

  // Multi-selection summary
  if (selectedObjectIds.size > 1) {
    // Determine if "Group" button should show:
    // Show when not all selected objects share the same groupId
    const selectedObjects = Array.from(selectedObjectIds)
      .map((id) => canvasObjects.get(id))
      .filter(Boolean) as CanvasObject[];
    const groupIds = new Set(selectedObjects.map((obj) => obj.groupId).filter(Boolean));
    const allInSameGroup =
      groupIds.size === 1 &&
      selectedObjects.every((obj) => obj.groupId === selectedObjects[0].groupId) &&
      selectedObjects[0].groupId !== undefined;
    const showGroupButton = !allInSameGroup;

    // Determine if "Ungroup" button should show:
    // Show when any selected object has a groupId
    const firstGroupId = selectedObjects.find((obj) => obj.groupId)?.groupId ?? null;
    const showUngroupButton = firstGroupId !== null;

    return (
      <div
        data-testid="bottom-panel"
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          backgroundColor: '#1e1e1e',
          borderTop: '1px solid rgba(255, 255, 255, 0.1)',
          zIndex: 50,
          color: 'rgba(255, 255, 255, 0.9)',
        }}
      >
        <div
          data-testid="multi-selection-summary"
          style={{
            padding: '16px 24px',
            fontSize: '14px',
            color: 'rgba(255, 255, 255, 0.7)',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <span>{selectedObjectIds.size} objects selected</span>
          {showGroupButton && (
            <button
              data-testid="group-button"
              onClick={() => groupSelectedObjects()}
              style={{
                padding: '4px 12px',
                fontSize: '12px',
                color: '#3b82f6',
                backgroundColor: 'transparent',
                border: '1px solid rgba(59, 130, 246, 0.4)',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              Group
            </button>
          )}
          {showUngroupButton && (
            <button
              data-testid="ungroup-button"
              onClick={() => ungroupObjects(firstGroupId!)}
              style={{
                padding: '4px 12px',
                fontSize: '12px',
                color: '#f59e0b',
                backgroundColor: 'transparent',
                border: '1px solid rgba(245, 158, 11, 0.4)',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              Ungroup
            </button>
          )}
        </div>
      </div>
    );
  }

  // Single selection — show config tabs
  if (!selectedObject) return null;

  return (
    <div
      data-testid="bottom-panel"
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        backgroundColor: '#1e1e1e',
        borderTop: '1px solid rgba(255, 255, 255, 0.1)',
        zIndex: 50,
        color: 'rgba(255, 255, 255, 0.9)',
      }}
    >
      {/* Tab bar */}
      <div
        data-testid="tab-bar"
        style={{
          display: 'flex',
          alignItems: 'center',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        }}
      >
        {tabs.map((tab) => {
          const isActive = tab === activeTab;
          return (
            <button
              key={tab}
              data-testid={`tab-${tab.toLowerCase()}`}
              onClick={() => setActiveTab(tab)}
              style={{
                padding: '10px 20px',
                fontSize: '13px',
                fontWeight: isActive ? 600 : 400,
                color: isActive ? '#fff' : 'rgba(255, 255, 255, 0.5)',
                backgroundColor: isActive ? '#2a2a2a' : 'transparent',
                borderTop: 'none',
                borderLeft: 'none',
                borderRight: 'none',
                borderBottomStyle: 'solid',
                borderBottomWidth: '2px',
                borderBottomColor: isActive ? '#3b82f6' : 'transparent',
                cursor: 'pointer',
              }}
            >
              {tab}
            </button>
          );
        })}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '12px', marginRight: '12px' }}>
          {selectedObjectId && <ZOrderControls objectId={selectedObjectId} />}
          <button
            data-testid="delete-object-button"
            onClick={() => {
              if (selectedObjectId) {
                removeCanvasObject(selectedObjectId);
              }
            }}
            style={{
              padding: '6px 12px',
              fontSize: '12px',
              color: '#ef4444',
              backgroundColor: 'transparent',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            🗑 Delete
          </button>
        </div>
      </div>

      {/* Tab content */}
      <div data-testid="tab-content" style={{ padding: '16px 24px' }}>
        {activeTab === 'Terraform' && selectedObject?.objectType === 'architecture-block' && (
          <div data-testid="terraform-tab-content">
            <TerraformTab block={selectedObject} />
          </div>
        )}
        {activeTab === 'Visual' && (
          <div data-testid="visual-tab-content">
            <VisualTab object={selectedObject} />
          </div>
        )}
      </div>
    </div>
  );
}
