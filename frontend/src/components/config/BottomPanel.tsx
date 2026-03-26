'use client';

import { useState, useEffect } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import type { CanvasObject } from '@/types/diagram';
import TerraformTab from './TerraformTab';
import VisualTab from './VisualTab';

/** Determine available tabs for a given canvas object type. */
export function getTabsForObject(obj: CanvasObject): string[] {
  if (obj.objectType === 'architecture-block') {
    return ['Terraform', 'Visual'];
  }
  return ['Visual'];
}

export default function BottomPanel() {
  const selectedObjectId = useDiagramStore((s) => s.selectedObjectId);
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);
  const removeCanvasObject = useDiagramStore((s) => s.removeCanvasObject);

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
  }, [selectedObjectId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Close panel when no object is selected
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
        <button
          data-testid="delete-object-button"
          onClick={() => {
            if (selectedObjectId) {
              removeCanvasObject(selectedObjectId);
            }
          }}
          style={{
            marginLeft: 'auto',
            marginRight: '12px',
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
