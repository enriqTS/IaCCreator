import fc from 'fast-check';
import { describe, it, expect, beforeEach } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';
import type { TextObject } from '@/types/diagram';
import { DEFAULT_TEXT_VISUAL } from '@/types/diagram';

/**
 * Feature: canvas-objects-editor, Property 7: Empty text objects are auto-removed
 * **Validates: Requirements 4.4**
 */
describe('Property 7: Empty text objects are auto-removed', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
      objectGroups: new Map(),
      elements: new Map(),
      connectors: new Map(),
      _undoStack: [],
      _redoStack: [],
      canUndo: false,
      canRedo: false,
    });
  });

  it('updating text content to empty or whitespace removes the object; non-empty content persists', () => {
    fc.assert(
      fc.property(
        fc.record({
          posX: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
          posY: fc.double({ min: -2000, max: 2000, noNaN: true, noDefaultInfinity: true }),
          newContent: fc.oneof(
            // Empty strings and whitespace-only
            fc.constant(''),
            fc.constant('   '),
            fc.constant('\t'),
            fc.constant('\n'),
            fc.constant('  \n\t  '),
            // Non-empty strings
            fc.string({ minLength: 1, maxLength: 100 }).filter((s) => s.trim().length > 0)
          ),
        }),
        ({ posX, posY, newContent }) => {
          const store = useDiagramStore.getState();

          // Create a text object with initial content
          const textId = store.addCanvasObject({
            objectType: 'text',
            name: 'Text',
            position: { x: posX, y: posY },
            content: 'initial content',
            visualConfig: { ...DEFAULT_TEXT_VISUAL },
          });

          // Verify it was created
          expect(useDiagramStore.getState().canvasObjects.has(textId)).toBe(true);

          // Update the text content
          useDiagramStore.getState().updateTextContent(textId, newContent);

          const isEmptyOrWhitespace = !newContent || newContent.trim() === '';

          if (isEmptyOrWhitespace) {
            // Object should be removed
            expect(useDiagramStore.getState().canvasObjects.has(textId)).toBe(false);
          } else {
            // Object should persist with new content
            const textObj = useDiagramStore.getState().canvasObjects.get(textId) as TextObject;
            expect(textObj).toBeDefined();
            expect(textObj.content).toBe(newContent);
          }

          // Clean up for next iteration
          useDiagramStore.setState({
            canvasObjects: new Map(),
            selectedObjectIds: new Set(),
            objectGroups: new Map(),
            _undoStack: [],
            _redoStack: [],
            canUndo: false,
            canRedo: false,
          });
        }
      ),
      { numRuns: 100 }
    );
  });
});
