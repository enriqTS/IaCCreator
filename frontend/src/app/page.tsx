'use client';

import { useState, useEffect, useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { useToastStore } from '@/store/toast-store';
import { useTourStore } from '@/store/tour-store';
import Canvas from '@/components/canvas/Canvas';
import Toolbar from '@/components/toolbar/Toolbar';
import HamburgerMenu from '@/components/menu/HamburgerMenu';
import SidebarPanel from '@/components/config/SidebarPanel';
import PreferencesDialog from '@/components/menu/PreferencesDialog';
import NewDiagramDialog from '@/components/menu/NewDiagramDialog';
import ProjectSettingsDialog from '@/components/menu/ProjectSettingsDialog';
import ToastProvider from '@/components/toast/ToastProvider';
import OnboardingTour from '@/components/tour/OnboardingTour';
import { saveDiagram, listSavedDiagrams, loadDiagram } from '@/utils/storage';
import { exportToTerraform } from '@/utils/export';

export default function DiagramEditorPage() {
  const [newDiagramOpen, setNewDiagramOpen] = useState(false);
  const [projectSettingsOpen, setProjectSettingsOpen] = useState(false);
  const [preferencesOpen, setPreferencesOpen] = useState(false);

  // Keyboard shortcuts
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement)?.tagName;
      const isTyping = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (e.target as HTMLElement)?.isContentEditable;

      const store = useDiagramStore.getState();

      if (!isTyping) {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z' && e.shiftKey) {
          e.preventDefault();
          store.redo();
          return;
        }
        if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
          e.preventDefault();
          store.undo();
          return;
        }
      }

      if (e.key === 'Delete' || e.key === 'Backspace') {
        // If typing inside an inline canvas editor (textarea/contenteditable), let it behave normally
        if (isTyping && (e.target as HTMLElement)?.closest('[data-testid="viewport-transform-container"]')) return;

        // If typing inside the sidebar config panel, blur the input and delete the object
        if (isTyping && (e.target as HTMLElement)?.closest('[data-testid="sidebar-panel"]')) {
          if (e.key === 'Backspace') return; // Let browser handle normal text editing
          if (store.selectedObjectIds.size > 0) {
            e.preventDefault();
            (document.activeElement as HTMLElement)?.blur();
            for (const id of store.selectedObjectIds) {
              store.removeCanvasObject(id);
            }
            return;
          }
          // No objects selected — let the input handle delete/backspace normally
          return;
        }

        // If typing in some other input (e.g. dialog), let it behave normally
        if (isTyping) return;

        e.preventDefault();
        if (store.selectedObjectIds.size > 0) {
          for (const id of store.selectedObjectIds) {
            store.removeCanvasObject(id);
          }
        } else if (store.selectedElementId) {
          const id = store.selectedElementId;
          store.removeElement(id);
          store.selectElement(null);
        } else if (store.selectedConnectorId) {
          const id = store.selectedConnectorId;
          store.removeConnector(id);
          store.selectConnector(null);
        }
        return;
      }

      if (!isTyping && e.key === 'Escape') {
        e.preventDefault();
        store.selectElement(null);
        store.selectConnector(null);
        store.selectObject(null);
        useDiagramStore.setState({ pendingConnectorSourceId: null });
        store.setActiveTool('pointer');
        return;
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const addToast = useToastStore((s) => s.addToast);
  const startTour = useTourStore((s) => s.startTour);

  const handleReplayTour = useCallback(() => {
    startTour();
  }, [startTour]);

  // HamburgerMenu callbacks
  const handleNewDiagram = useCallback(() => {
    setNewDiagramOpen(true);
  }, []);

  const handleSave = useCallback(() => {
    try {
      const store = useDiagramStore.getState();
      const name = store.projectName || 'untitled';
      const state = store.serializeDiagramState();
      const result = saveDiagram(name, state);
      if (result.success) {
        addToast(`Diagram saved as "${name}"`, 'success');
      } else {
        addToast(`Save failed: ${result.error}`, 'error');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown save error';
      addToast(`Save failed: ${msg}`, 'error');
    }
  }, [addToast]);

  const handleLoad = useCallback(() => {
    try {
      const saved = listSavedDiagrams();
      if (saved.length === 0) {
        addToast('No saved diagrams found.', 'error');
        return;
      }
      // Load the most recently saved diagram
      const latest = saved.sort(
        (a, b) => new Date(b.savedAt).getTime() - new Date(a.savedAt).getTime(),
      )[0];
      const result = loadDiagram(latest.name);
      if (result.success && result.state) {
        useDiagramStore.getState().loadDiagramState(result.state);
        addToast(`Loaded diagram "${latest.name}"`, 'success');
      } else {
        addToast(`Load failed: ${result.error}`, 'error');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown load error';
      addToast(`Load failed: ${msg}`, 'error');
    }
  }, [addToast]);

  const handleExport = useCallback(async () => {
    try {
      const store = useDiagramStore.getState();
      const result = await exportToTerraform(
        store.serializeToArchitectureDescription,
        store.canvasObjects,
      );
      if (result.success) {
        addToast('Terraform export downloaded successfully!', 'success');
      } else {
        const msg = result.fieldErrors
          ? `${result.error}: ${Object.values(result.fieldErrors).join(', ')}`
          : result.error ?? 'Export failed';
        addToast(msg, 'error');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown export error';
      addToast(`Export failed: ${msg}`, 'error');
    }
  }, [addToast]);

  const handleProjectSettings = useCallback(() => {
    setProjectSettingsOpen(true);
  }, []);

  return (
    <div
      style={{
        width: '100vw',
        height: '100vh',
        overflow: 'hidden',
        background: '#121212',
        position: 'relative',
      }}
    >
      <Canvas />
      <Toolbar />
      <HamburgerMenu
        onNewDiagram={handleNewDiagram}
        onSave={handleSave}
        onLoad={handleLoad}
        onExport={handleExport}
        onProjectSettings={handleProjectSettings}
        onPreferences={() => setPreferencesOpen(true)}
        onReplayTour={handleReplayTour}
      />
      <SidebarPanel />
      <NewDiagramDialog
        open={newDiagramOpen}
        onClose={() => setNewDiagramOpen(false)}
      />
      <ProjectSettingsDialog
        open={projectSettingsOpen}
        onClose={() => setProjectSettingsOpen(false)}
      />
      <PreferencesDialog
        open={preferencesOpen}
        onClose={() => setPreferencesOpen(false)}
      />
      <ToastProvider />
      <OnboardingTour />
    </div>
  );
}
