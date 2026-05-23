import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import type { ArchitectureBlock } from '@/types/diagram';
import { DEFAULT_BLOCK_VISUAL } from '@/types/diagram';

/**
 * **Validates: Requirements 1.1, 1.2**
 *
 * Property 1: Bug Condition — Backspace in Sidebar Deletes Objects
 *
 * This test encodes the EXPECTED (correct) behavior: pressing Backspace while
 * typing in a sidebar input/textarea with canvas objects selected should allow
 * normal text editing — it should NOT call preventDefault, should NOT blur the
 * input, and should NOT delete any canvas objects.
 *
 * On UNFIXED code, this test is EXPECTED TO FAIL because the handlers treat
 * Backspace identically to Delete in the sidebar branch.
 *
 * Bug Condition: isBugCondition(input) where:
 *   input.key === 'Backspace' AND isTyping AND isInSidebar AND selectedObjectIds.size > 0
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

describe('Property 1: Bug Condition — Backspace in Sidebar Deletes Objects', () => {
  let sidebarPanel: HTMLDivElement;
  let removeCanvasObjectSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    // Create a sidebar panel container in the DOM
    sidebarPanel = document.createElement('div');
    sidebarPanel.setAttribute('data-testid', 'sidebar-panel');
    document.body.appendChild(sidebarPanel);

    // Reset store
    useDiagramStore.setState({
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
    });
  });

  afterEach(() => {
    document.body.removeChild(sidebarPanel);
    if (removeCanvasObjectSpy) {
      removeCanvasObjectSpy.mockRestore();
    }
  });

  test('Property-based: Backspace in sidebar input/textarea with selected objects should NOT prevent default, blur, or delete objects', async () => {
    // Import Canvas to attach the keydown listener (handleDeleteKey)
    const { default: Canvas } = await import('@/components/canvas/Canvas');
    const { render, cleanup } = await import('@testing-library/react');
    const { unmount } = render(<Canvas />);

    fc.assert(
      fc.property(
        // Generate target type: INPUT or TEXTAREA
        fc.constantFrom('INPUT', 'TEXTAREA'),
        // Generate number of selected objects (1 to 5)
        fc.integer({ min: 1, max: 5 }),
        (targetType, selectedObjectCount) => {
          // Setup: create canvas objects and select them
          const objects = new Map<string, ArchitectureBlock>();
          const selectedIds = new Set<string>();
          for (let i = 0; i < selectedObjectCount; i++) {
            const id = `obj-${i}`;
            objects.set(id, makeBlock(id));
            selectedIds.add(id);
          }
          useDiagramStore.setState({
            canvasObjects: objects as Map<string, ArchitectureBlock>,
            selectedObjectIds: selectedIds,
          });

          // Spy on removeCanvasObject
          const storeSpy = vi.spyOn(useDiagramStore.getState(), 'removeCanvasObject');

          // Create target element inside sidebar panel
          const target = document.createElement(targetType.toLowerCase());
          sidebarPanel.appendChild(target);
          target.focus();

          // Dispatch Backspace KeyboardEvent to the target
          const event = new KeyboardEvent('keydown', {
            key: 'Backspace',
            code: 'Backspace',
            bubbles: true,
            cancelable: true,
          });
          target.dispatchEvent(event);

          // Assertions: Backspace should NOT be prevented (normal text editing)
          expect(event.defaultPrevented).toBe(false);

          // Assertions: input should remain focused (NOT blurred)
          expect(document.activeElement).toBe(target);

          // Assertions: removeCanvasObject should NOT have been called
          expect(storeSpy).not.toHaveBeenCalled();

          // Assertions: objects should still exist in the store
          const state = useDiagramStore.getState();
          expect(state.canvasObjects.size).toBe(selectedObjectCount);
          expect(state.selectedObjectIds.size).toBe(selectedObjectCount);

          // Cleanup
          storeSpy.mockRestore();
          sidebarPanel.removeChild(target);
        },
      ),
      { numRuns: 20 },
    );

    unmount();
  });
});
