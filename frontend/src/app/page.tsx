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
import KeyboardShortcutsOverlay from '@/components/shortcuts/KeyboardShortcutsOverlay';
import { saveDiagram, listSavedDiagrams, loadDiagram } from '@/utils/storage';
import { exportToTerraform } from '@/utils/export';

export default function DiagramEditorPage() {
  const [newDiagramOpen, setNewDiagramOpen] = useState(false);
  const [projectSettingsOpen, setProjectSettingsOpen] = useState(false);
  const [preferencesOpen, setPreferencesOpen] = useState(false);
  const [shortcutsOverlayOpen, setShortcutsOverlayOpen] = useState(false);

  // Keyboard shortcuts
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement)?.tagName;
      const isTyping = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (e.target as HTMLElement)?.isContentEditable;

      const store = useDiagramStore.getState();
      const mod = e.ctrlKey || e.metaKey;

      // --- Shortcuts that work even when not typing ---

      if (!isTyping) {
        // Help overlay
        if (e.key === '?' && !mod) {
          e.preventDefault();
          setShortcutsOverlayOpen((prev) => !prev);
          return;
        }

        // Undo / Redo
        if (mod && e.key.toLowerCase() === 'z' && e.shiftKey) {
          e.preventDefault();
          store.redo();
          return;
        }
        if (mod && e.key === 'z' && !e.shiftKey) {
          e.preventDefault();
          store.undo();
          return;
        }

        // Copy / Cut / Paste / Duplicate
        if (mod && e.key === 'c' && !e.shiftKey) {
          e.preventDefault();
          store.copySelectedObjects();
          return;
        }
        if (mod && e.key === 'x' && !e.shiftKey) {
          e.preventDefault();
          store.copySelectedObjects();
          for (const id of store.selectedObjectIds) {
            store.removeCanvasObject(id);
          }
          return;
        }
        if (mod && e.key === 'v' && !e.shiftKey) {
          e.preventDefault();
          // Paste at center of viewport
          const { viewport } = store;
          const centerX = (window.innerWidth / 2 - viewport.offsetX) / viewport.scale;
          const centerY = (window.innerHeight / 2 - viewport.offsetY) / viewport.scale;
          store.pasteObjects({ x: centerX, y: centerY });
          return;
        }
        if (mod && e.key === 'd' && !e.shiftKey) {
          e.preventDefault();
          store.duplicateSelectedObjects();
          return;
        }

        // Select All
        if (mod && e.key === 'a' && !e.shiftKey) {
          e.preventDefault();
          store.selectAllObjects();
          return;
        }

        // Group / Ungroup
        if (mod && e.key === 'g' && !e.shiftKey) {
          e.preventDefault();
          store.groupSelectedObjects();
          return;
        }
        if (mod && e.key === 'g' && e.shiftKey) {
          e.preventDefault();
          // Ungroup: find the group of any selected object
          for (const id of store.selectedObjectIds) {
            const obj = store.canvasObjects.get(id);
            if (obj?.groupId) {
              store.ungroupObjects(obj.groupId);
              break;
            }
          }
          return;
        }

        // Lock / Unlock
        if (mod && e.key === 'l' && !e.shiftKey) {
          e.preventDefault();
          if (store.selectedObjectIds.size > 0) {
            store.toggleLockObjects(store.selectedObjectIds);
          }
          return;
        }

        // Z-order: brackets
        if (e.key === ']' && !mod) {
          e.preventDefault();
          for (const id of store.selectedObjectIds) {
            store.bringForward(id);
          }
          return;
        }
        if (e.key === '[' && !mod) {
          e.preventDefault();
          for (const id of store.selectedObjectIds) {
            store.sendBackward(id);
          }
          return;
        }
        if (mod && e.key === ']') {
          e.preventDefault();
          for (const id of store.selectedObjectIds) {
            store.bringToFront(id);
          }
          return;
        }
        if (mod && e.key === '[') {
          e.preventDefault();
          for (const id of store.selectedObjectIds) {
            store.sendToBack(id);
          }
          return;
        }

        // Zoom
        if (mod && (e.key === '=' || e.key === '+')) {
          e.preventDefault();
          const center = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
          store.zoom(1.2, center);
          return;
        }
        if (mod && e.key === '-') {
          e.preventDefault();
          const center = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
          store.zoom(0.8, center);
          return;
        }
        if (mod && e.key === '0') {
          e.preventDefault();
          store.fitToScreen({ width: window.innerWidth, height: window.innerHeight });
          return;
        }
        if (mod && e.key === '1') {
          e.preventDefault();
          // Reset to 100% zoom centered on current view
          const { viewport } = store;
          const centerX = window.innerWidth / 2;
          const centerY = window.innerHeight / 2;
          const factor = 1 / viewport.scale;
          store.zoom(factor, { x: centerX, y: centerY });
          return;
        }

        // Tool shortcuts (single keys, no modifiers)
        if (!mod && !e.shiftKey && !e.altKey) {
          switch (e.key.toLowerCase()) {
            case 'v':
              e.preventDefault();
              store.setActiveTool('pointer');
              return;
            case 'c':
              e.preventDefault();
              store.setActiveTool('connector');
              return;
            case 'l':
              e.preventDefault();
              store.setActiveTool('line');
              return;
            case 't':
              e.preventDefault();
              store.setActiveTool('text');
              return;
          }
        }
      }

      // --- Delete / Backspace (works with special isTyping rules) ---
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
          return;
        }

        // If typing in some other input (e.g. dialog), let it behave normally
        if (isTyping) return;

        e.preventDefault();
        if (store.selectedObjectIds.size > 0) {
          for (const id of store.selectedObjectIds) {
            store.removeCanvasObject(id);
          }
        } else if (store.selectedConnectorId) {
          const id = store.selectedConnectorId;
          store.removeConnector(id);
          store.selectConnector(null);
        }
        return;
      }

      // --- Escape ---
      if (!isTyping && e.key === 'Escape') {
        e.preventDefault();
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
      <KeyboardShortcutsOverlay
        isOpen={shortcutsOverlayOpen}
        onClose={() => setShortcutsOverlayOpen(false)}
      />
    </div>
  );
}
