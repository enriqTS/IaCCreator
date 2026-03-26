import { describe, it, expect, beforeEach } from 'vitest';
import {
  saveDiagram,
  loadDiagram,
  listSavedDiagrams,
  deleteSavedDiagram,
} from '@/utils/storage';
import type { DiagramState } from '@/types/serialization';

function makeDiagramState(overrides?: Partial<DiagramState>): DiagramState {
  return {
    version: 1,
    projectName: 'test-project',
    environments: [],
    elements: [],
    connectors: [],
    viewport: { offsetX: 0, offsetY: 0, scale: 1 },
    ...overrides,
  };
}

describe('storage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('saveDiagram', () => {
    it('saves a diagram and returns success', () => {
      const state = makeDiagramState();
      const result = saveDiagram('my-diagram', state);
      expect(result.success).toBe(true);
      expect(result.error).toBeUndefined();

      const raw = localStorage.getItem('diagram-editor:my-diagram');
      expect(raw).not.toBeNull();
      const parsed = JSON.parse(raw!);
      expect(parsed.state).toEqual(state);
      expect(parsed.savedAt).toBeDefined();
    });

    it('returns error on quota exceeded', () => {
      const original = Storage.prototype.setItem;
      Storage.prototype.setItem = () => {
        const err = new DOMException('quota exceeded', 'QuotaExceededError');
        throw err;
      };

      const result = saveDiagram('big', makeDiagramState());
      expect(result.success).toBe(false);
      expect(result.error).toContain('quota');

      Storage.prototype.setItem = original;
    });
  });

  describe('loadDiagram', () => {
    it('loads a previously saved diagram', () => {
      const state = makeDiagramState({ projectName: 'loaded' });
      saveDiagram('saved-one', state);

      const result = loadDiagram('saved-one');
      expect(result.success).toBe(true);
      expect(result.state).toEqual(state);
    });

    it('returns error for non-existent diagram', () => {
      const result = loadDiagram('nope');
      expect(result.success).toBe(false);
      expect(result.error).toContain('not found');
    });

    it('returns error for corrupted JSON', () => {
      localStorage.setItem('diagram-editor:bad', '{not valid json');
      const result = loadDiagram('bad');
      expect(result.success).toBe(false);
      expect(result.error).toContain('corrupted');
    });

    it('returns error for missing state field', () => {
      localStorage.setItem('diagram-editor:empty', JSON.stringify({ savedAt: 'now' }));
      const result = loadDiagram('empty');
      expect(result.success).toBe(false);
      expect(result.error).toContain('corrupted');
    });

    it('returns error for version mismatch', () => {
      const state = makeDiagramState({ version: 99 });
      localStorage.setItem(
        'diagram-editor:old',
        JSON.stringify({ savedAt: 'now', state })
      );
      const result = loadDiagram('old');
      expect(result.success).toBe(false);
      expect(result.error).toContain('version');
    });
  });

  describe('listSavedDiagrams', () => {
    it('returns empty array when no diagrams saved', () => {
      expect(listSavedDiagrams()).toEqual([]);
    });

    it('lists all saved diagrams', () => {
      saveDiagram('alpha', makeDiagramState());
      saveDiagram('beta', makeDiagramState());

      const list = listSavedDiagrams();
      const names = list.map((d) => d.name).sort();
      expect(names).toEqual(['alpha', 'beta']);
      for (const entry of list) {
        expect(entry.savedAt).toBeTruthy();
      }
    });

    it('skips corrupted entries', () => {
      saveDiagram('good', makeDiagramState());
      localStorage.setItem('diagram-editor:bad', '{broken');

      const list = listSavedDiagrams();
      expect(list).toHaveLength(1);
      expect(list[0].name).toBe('good');
    });

    it('ignores non-diagram localStorage keys', () => {
      localStorage.setItem('other-key', 'value');
      saveDiagram('mine', makeDiagramState());

      const list = listSavedDiagrams();
      expect(list).toHaveLength(1);
      expect(list[0].name).toBe('mine');
    });
  });

  describe('deleteSavedDiagram', () => {
    it('removes a saved diagram', () => {
      saveDiagram('to-delete', makeDiagramState());
      expect(listSavedDiagrams()).toHaveLength(1);

      deleteSavedDiagram('to-delete');
      expect(listSavedDiagrams()).toHaveLength(0);
      expect(localStorage.getItem('diagram-editor:to-delete')).toBeNull();
    });

    it('does nothing for non-existent diagram', () => {
      deleteSavedDiagram('ghost');
      // no error thrown
    });
  });
});
