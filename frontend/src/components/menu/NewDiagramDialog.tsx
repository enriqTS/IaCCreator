'use client';

import { useEffect, useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { Button } from '@/components/ui/button';

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
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-[100]"
    >
      <div
        data-testid="new-diagram-dialog"
        onClick={(e) => e.stopPropagation()}
        className="bg-[#1e1e1e] rounded-xl p-6 min-w-[360px] text-[#e5e5e5] shadow-[0_8px_32px_rgba(0,0,0,0.5)]"
      >
        <h2 className="m-0 mb-3 text-lg font-semibold">New Diagram</h2>
        <p className="m-0 mb-6 text-sm text-muted-foreground">
          Create a new diagram? This will clear the current diagram.
        </p>
        <div className="flex justify-end gap-2">
          <Button
            data-testid="new-diagram-cancel"
            variant="outline"
            onClick={onClose}
          >
            Cancel
          </Button>
          <Button
            data-testid="new-diagram-confirm"
            variant="destructive"
            onClick={handleConfirm}
          >
            Confirm
          </Button>
        </div>
      </div>
    </div>
  );
}
