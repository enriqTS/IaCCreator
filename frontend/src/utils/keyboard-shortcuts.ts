/**
 * Keyboard Shortcuts System
 *
 * Centralized registry for keyboard shortcuts with human-readable descriptions.
 * Provides a hook for listening to shortcuts and a data structure for the help overlay.
 */

/** A single keyboard shortcut definition. */
export interface ShortcutDef {
  /** Unique identifier for the shortcut. */
  id: string;
  /** Human-readable description shown in help overlay. */
  description: string;
  /** Display string for the key combination (e.g., "Ctrl+Z"). */
  keys: string;
  /** Category for grouping in the help overlay. */
  category: ShortcutCategory;
}

export type ShortcutCategory = 'General' | 'Edit' | 'View' | 'Tools' | 'Objects';

/**
 * Complete shortcut registry — source of truth for all app shortcuts.
 * Order within each category determines display order in the help overlay.
 */
export const SHORTCUTS: ShortcutDef[] = [
  // General
  { id: 'help', description: 'Show keyboard shortcuts', keys: '?', category: 'General' },
  { id: 'escape', description: 'Cancel / Deselect all', keys: 'Esc', category: 'General' },
  { id: 'delete', description: 'Delete selected', keys: 'Del / Backspace', category: 'General' },
  { id: 'select-all', description: 'Select all objects', keys: 'Ctrl+A', category: 'General' },

  // Edit
  { id: 'undo', description: 'Undo', keys: 'Ctrl+Z', category: 'Edit' },
  { id: 'redo', description: 'Redo', keys: 'Ctrl+Shift+Z', category: 'Edit' },
  { id: 'copy', description: 'Copy selected', keys: 'Ctrl+C', category: 'Edit' },
  { id: 'paste', description: 'Paste', keys: 'Ctrl+V', category: 'Edit' },
  { id: 'cut', description: 'Cut selected', keys: 'Ctrl+X', category: 'Edit' },
  { id: 'duplicate', description: 'Duplicate selected', keys: 'Ctrl+D', category: 'Edit' },

  // Objects
  { id: 'group', description: 'Group selected', keys: 'Ctrl+G', category: 'Objects' },
  { id: 'ungroup', description: 'Ungroup', keys: 'Ctrl+Shift+G', category: 'Objects' },
  { id: 'bring-forward', description: 'Bring forward', keys: ']', category: 'Objects' },
  { id: 'send-backward', description: 'Send backward', keys: '[', category: 'Objects' },
  { id: 'bring-to-front', description: 'Bring to front', keys: 'Ctrl+]', category: 'Objects' },
  { id: 'send-to-back', description: 'Send to back', keys: 'Ctrl+[', category: 'Objects' },
  { id: 'lock', description: 'Lock / Unlock selected', keys: 'Ctrl+L', category: 'Objects' },

  // View
  { id: 'zoom-in', description: 'Zoom in', keys: 'Ctrl+=', category: 'View' },
  { id: 'zoom-out', description: 'Zoom out', keys: 'Ctrl+-', category: 'View' },
  { id: 'zoom-fit', description: 'Zoom to fit', keys: 'Ctrl+0', category: 'View' },
  { id: 'zoom-100', description: 'Zoom to 100%', keys: 'Ctrl+1', category: 'View' },

  // Tools
  { id: 'tool-pointer', description: 'Pointer tool', keys: 'V', category: 'Tools' },
  { id: 'tool-connector', description: 'Connector tool', keys: 'C', category: 'Tools' },
  { id: 'tool-line', description: 'Line tool', keys: 'L', category: 'Tools' },
  { id: 'tool-text', description: 'Text tool', keys: 'T', category: 'Tools' },
];

/**
 * Get shortcuts grouped by category for rendering in the help overlay.
 */
export function getShortcutsByCategory(): Record<ShortcutCategory, ShortcutDef[]> {
  const grouped: Record<ShortcutCategory, ShortcutDef[]> = {
    General: [],
    Edit: [],
    View: [],
    Tools: [],
    Objects: [],
  };

  for (const shortcut of SHORTCUTS) {
    grouped[shortcut.category].push(shortcut);
  }

  return grouped;
}
