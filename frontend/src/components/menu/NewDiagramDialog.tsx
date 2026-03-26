'use client';

import { useEffect, useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';

export interface NewDiagramDialogProps {
  open: boolean;
  onClose: () => void;
}

export default function NewDiagramDialog({ open, onClose }: NewDiagramDialogProps) {
  const handleConfirm = useCallback(() => {
    const store = useDiagramStore.getState();
    // Clear all elements and connectors
    useDiagramStore.setState({
      elements: new Map(),
      connectors: new Map(),
      viewport: { offsetX: 0, offsetY: 0, scale: 1 },
      projectName: '',
      environments: [],
      selectedElementId: null,
      selectedConnectorId: null,
      pendingConnectorSourceId: null,
      activeTool: 'pointer',
      _undoStack: [],
      _redoStack: [],
      canUndo: false,
      canRedo: false,
    });
    onClose();
  }, [onClose]);

  // Close on Escape key
  useEffect(() => {
    if (!open) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        onClose();
      }
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      data-testid="new-diagram-overlay"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0, 0, 0, 0.6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 100,
      }}
    >
      <div
        data-testid="new-diagram-dialog"
        onClick={(e) => e.stopPropagation()}
        style={{
          background: '#1e1e1e',
          borderRadius: 12,
          padding: 24,
          minWidth: 360,
          color: '#e5e5e5',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
        }}
      >
        <h2 style={{ margin: '0 0 12px', fontSize: 18, fontWeight: 600 }}>New Diagram</h2>
        <p style={{ margin: '0 0 24px', fontSize: 14, color: '#a3a3a3' }}>
          Create a new diagram? This will clear the current diagram.
        </p>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <button
            data-testid="new-diagram-cancel"
            onClick={onClose}
            style={{
              padding: '8px 16px',
              borderRadius: 6,
              border: '1px solid #404040',
              background: 'transparent',
              color: '#e5e5e5',
              fontSize: 14,
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            data-testid="new-diagram-confirm"
            onClick={handleConfirm}
            style={{
              padding: '8px 16px',
              borderRadius: 6,
              border: 'none',
              background: '#ef4444',
              color: '#fff',
              fontSize: 14,
              cursor: 'pointer',
            }}
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}
