import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import type { ArchitectureBlock } from '@/types/diagram';
import { DEFAULT_BLOCK_VISUAL } from '@/types/diagram';

/**
 * **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
 *
 * Property 2: Preservation — Delete Key and Non-Sidebar Behavior Unchanged
 *
 * These tests capture the CURRENT correct behavior (non-bug cases) on UNFIXED code.
 * They verify that:
 * - Delete in sidebar with selection → blurs input, calls removeCanvasObject
 * - Backspace/Delete on canvas (no input focused) with selection → calls removeCanvasObject
 * - Backspace in viewport-transform-container input → normal text editing (no preventDefault)
 * - Backspace in dialog input → normal text editing (no preventDefault)
 * - No selection, no focus → no action
 *
 * All these tests should PASS on unfixed code.
 */

function makeBlock(id: string): ArchitectureBlock {
  return {
    id,
    objectType: 'architecture-block',
    serviceType: 'lambda',
    name: `block-${id}`,
    position: { x: 0, y: 0 },
    config: {},
    terraformVariables: { function_name: '', handler: '', runtime: '', memory_size: 128, timeout: 3 },
    visualConfig: { ...DEFAULT_BLOCK_VISUAL },
    zIndex: 0,
  };
}

function setupStoreWithObjects(count: number) {
  const objects = new Map<string, ArchitectureBlock>();
  const selectedIds = new Set<string>();
  for (let i = 0; i < count; i++) {
    const id = `obj-${i}`;
    objects.set(id, makeBlock(id));
    selectedIds.add(id);
  }
  useDiagramStore.setState({
    canvasObjects: objects as Map<string, ArchitectureBlock>,
    selectedObjectIds: selectedIds,
  });
  return { objects, selectedIds };
}

describe('Property 2: Preservation — Delete Key and Non-Sidebar Behavior Unchanged', () => {
  let sidebarPanel: HTMLDivElement;
  let viewportContainer: HTMLDivElement;
  let dialogContainer: HTMLDivElement;

  beforeEach(() => {
    // Create DOM containers
    sidebarPanel = document.createElement('div');
    sidebarPanel.setAttribute('data-testid', 'sidebar-panel');
    document.body.appendChild(sidebarPanel);

    viewportContainer = document.createElement('div');
    viewportContainer.setAttribute('data-testid', 'viewport-transform-container');
    document.body.appendChild(viewportContainer);

    dialogContainer = document.createElement('div');
    dialogContainer.setAttribute('role', 'dialog');
    document.body.appendChild(dialogContainer);

    // Reset store
    useDiagramStore.setState({
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
    });
  });

  afterEach(() => {
    document.body.removeChild(sidebarPanel);
    document.body.removeChild(viewportContainer);
    document.body.removeChild(dialogContainer);
  });

  test('Preservation: Delete in sidebar with selection → preventDefault called, objects removed', async () => {
    const { default: Canvas } = await import('@/components/canvas/Canvas');
    const { render } = await import('@testing-library/react');
    const { unmount } = render(<Canvas />);

    fc.assert(
      fc.property(
        fc.constantFrom('INPUT', 'TEXTAREA'),
        fc.integer({ min: 1, max: 5 }),
        (targetType, selectedObjectCount) => {
          setupStoreWithObjects(selectedObjectCount);

          // Create target element inside sidebar panel
          const target = document.createElement(targetType.toLowerCase());
          sidebarPanel.appendChild(target);
          target.focus();

          // Dispatch Delete KeyboardEvent
          const event = new KeyboardEvent('keydown', {
            key: 'Delete',
            code: 'Delete',
            bubbles: true,
            cancelable: true,
          });
          target.dispatchEvent(event);

          // Delete in sidebar with selection: preventDefault IS called
          expect(event.defaultPrevented).toBe(true);

          // Input should be blurred (activeElement is not the target)
          expect(document.activeElement).not.toBe(target);

          // Objects should be removed
          const state = useDiagramStore.getState();
          expect(state.canvasObjects.size).toBe(0);

          // Cleanup
          sidebarPanel.removeChild(target);
        },
      ),
      { numRuns: 20 },
    );

    unmount();
  });

  test('Preservation: Backspace/Delete on canvas (no input focused) with selection → objects removed', async () => {
    const { default: Canvas } = await import('@/components/canvas/Canvas');
    const { render } = await import('@testing-library/react');
    const { unmount } = render(<Canvas />);

    fc.assert(
      fc.property(
        fc.constantFrom('Backspace', 'Delete'),
        fc.integer({ min: 1, max: 5 }),
        (key, selectedObjectCount) => {
          setupStoreWithObjects(selectedObjectCount);

          // Dispatch key event on window (no input focused — simulates canvas focus)
          const event = new KeyboardEvent('keydown', {
            key,
            code: key,
            bubbles: true,
            cancelable: true,
          });
          window.dispatchEvent(event);

          // preventDefault IS called (canvas deletion behavior)
          expect(event.defaultPrevented).toBe(true);

          // Objects should be removed
          const state = useDiagramStore.getState();
          expect(state.canvasObjects.size).toBe(0);
        },
      ),
      { numRuns: 20 },
    );

    unmount();
  });

  test('Preservation: Backspace in viewport-transform-container input → normal text editing (no preventDefault)', async () => {
    const { default: Canvas } = await import('@/components/canvas/Canvas');
    const { render } = await import('@testing-library/react');
    const { unmount } = render(<Canvas />);

    fc.assert(
      fc.property(
        fc.constantFrom('INPUT', 'TEXTAREA'),
        fc.integer({ min: 1, max: 5 }),
        (targetType, selectedObjectCount) => {
          setupStoreWithObjects(selectedObjectCount);

          // Create target element inside viewport-transform-container
          const target = document.createElement(targetType.toLowerCase());
          viewportContainer.appendChild(target);
          target.focus();

          // Dispatch Backspace KeyboardEvent
          const event = new KeyboardEvent('keydown', {
            key: 'Backspace',
            code: 'Backspace',
            bubbles: true,
            cancelable: true,
          });
          target.dispatchEvent(event);

          // Backspace in viewport-transform-container: NOT prevented
          expect(event.defaultPrevented).toBe(false);

          // Objects should NOT be removed
          const state = useDiagramStore.getState();
          expect(state.canvasObjects.size).toBe(selectedObjectCount);

          // Cleanup
          viewportContainer.removeChild(target);
        },
      ),
      { numRuns: 20 },
    );

    unmount();
  });

  test('Preservation: Backspace in dialog input → normal text editing (no preventDefault)', async () => {
    const { default: Canvas } = await import('@/components/canvas/Canvas');
    const { render } = await import('@testing-library/react');
    const { unmount } = render(<Canvas />);

    fc.assert(
      fc.property(
        fc.constantFrom('INPUT', 'TEXTAREA'),
        fc.integer({ min: 1, max: 5 }),
        (targetType, selectedObjectCount) => {
          setupStoreWithObjects(selectedObjectCount);

          // Create target element inside dialog (not sidebar, not viewport)
          const target = document.createElement(targetType.toLowerCase());
          dialogContainer.appendChild(target);
          target.focus();

          // Dispatch Backspace KeyboardEvent
          const event = new KeyboardEvent('keydown', {
            key: 'Backspace',
            code: 'Backspace',
            bubbles: true,
            cancelable: true,
          });
          target.dispatchEvent(event);

          // Backspace in dialog: NOT prevented
          expect(event.defaultPrevented).toBe(false);

          // Objects should NOT be removed
          const state = useDiagramStore.getState();
          expect(state.canvasObjects.size).toBe(selectedObjectCount);

          // Cleanup
          dialogContainer.removeChild(target);
        },
      ),
      { numRuns: 20 },
    );

    unmount();
  });

  test('Preservation: No selection, no focus → no action on Backspace/Delete', async () => {
    const { default: Canvas } = await import('@/components/canvas/Canvas');
    const { render } = await import('@testing-library/react');
    const { unmount } = render(<Canvas />);

    fc.assert(
      fc.property(
        fc.constantFrom('Backspace', 'Delete'),
        (key) => {
          // Setup: objects exist but NONE are selected
          const objects = new Map<string, ArchitectureBlock>();
          objects.set('obj-0', makeBlock('obj-0'));
          useDiagramStore.setState({
            canvasObjects: objects as Map<string, ArchitectureBlock>,
            selectedObjectIds: new Set(),
            selectedElementId: null,
            selectedConnectorId: null,
          });

          // Dispatch key event on window (no input focused)
          const event = new KeyboardEvent('keydown', {
            key,
            code: key,
            bubbles: true,
            cancelable: true,
          });
          window.dispatchEvent(event);

          // Objects should NOT be removed (nothing selected)
          const state = useDiagramStore.getState();
          expect(state.canvasObjects.size).toBe(1);
          expect(state.canvasObjects.has('obj-0')).toBe(true);
        },
      ),
      { numRuns: 10 },
    );

    unmount();
  });
});
