/**
 * localStorage-based save/load for diagram state.
 */

import type { DiagramState } from '@/types/serialization';

const STORAGE_PREFIX = 'diagram-editor:';
const CURRENT_VERSION = 1;

export interface SaveResult {
  success: boolean;
  error?: string;
}

export interface LoadResult {
  success: boolean;
  state?: DiagramState;
  error?: string;
}

export interface SavedDiagramEntry {
  name: string;
  savedAt: string;
}

interface StoredDiagram {
  savedAt: string;
  state: DiagramState;
}

/**
 * Save a diagram state to localStorage under the given name.
 * Returns success/error result — catches quota exceeded errors.
 */
export function saveDiagram(name: string, state: DiagramState): SaveResult {
  const key = `${STORAGE_PREFIX}${name}`;
  const entry: StoredDiagram = {
    savedAt: new Date().toISOString(),
    state,
  };

  try {
    localStorage.setItem(key, JSON.stringify(entry));
    return { success: true };
  } catch (err: unknown) {
    if (
      err instanceof DOMException &&
      (err.name === 'QuotaExceededError' || err.code === 22)
    ) {
      return {
        success: false,
        error: 'Storage quota exceeded. Try deleting old diagrams to free space.',
      };
    }
    return {
      success: false,
      error: err instanceof Error ? err.message : 'Failed to save diagram.',
    };
  }
}

/**
 * Load a diagram state from localStorage by name.
 * Validates JSON parsing and version field.
 */
export function loadDiagram(name: string): LoadResult {
  const key = `${STORAGE_PREFIX}${name}`;
  const raw = localStorage.getItem(key);

  if (raw === null) {
    return { success: false, error: `Diagram "${name}" not found.` };
  }

  let entry: StoredDiagram;
  try {
    entry = JSON.parse(raw) as StoredDiagram;
  } catch {
    return { success: false, error: `Diagram "${name}" has corrupted data.` };
  }

  if (!entry.state) {
    return { success: false, error: `Diagram "${name}" has corrupted data.` };
  }

  if (entry.state.version !== CURRENT_VERSION) {
    return {
      success: false,
      error: `Diagram "${name}" was saved with version ${entry.state.version}, but current version is ${CURRENT_VERSION}.`,
    };
  }

  return { success: true, state: entry.state };
}

/**
 * List all saved diagrams from localStorage.
 * Skips entries with corrupted JSON silently.
 */
export function listSavedDiagrams(): SavedDiagramEntry[] {
  const results: SavedDiagramEntry[] = [];

  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (!key || !key.startsWith(STORAGE_PREFIX)) continue;

    const name = key.slice(STORAGE_PREFIX.length);
    const raw = localStorage.getItem(key);
    if (!raw) continue;

    try {
      const entry = JSON.parse(raw) as StoredDiagram;
      results.push({ name, savedAt: entry.savedAt ?? '' });
    } catch {
      // Skip corrupted entries
    }
  }

  return results;
}

/**
 * Delete a saved diagram from localStorage.
 */
export function deleteSavedDiagram(name: string): void {
  const key = `${STORAGE_PREFIX}${name}`;
  localStorage.removeItem(key);
}
