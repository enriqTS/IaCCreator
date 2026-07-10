'use client';

import { useEffect } from 'react';
import { getShortcutsByCategory } from '@/utils/keyboard-shortcuts';
import type { ShortcutCategory } from '@/utils/keyboard-shortcuts';

interface KeyboardShortcutsOverlayProps {
  isOpen: boolean;
  onClose: () => void;
}

const CATEGORY_ORDER: ShortcutCategory[] = ['General', 'Edit', 'Objects', 'View', 'Tools'];

export default function KeyboardShortcutsOverlay({ isOpen, onClose }: KeyboardShortcutsOverlayProps) {
  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' || e.key === '?') {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const grouped = getShortcutsByCategory();

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50"
      onClick={onClose}
      role="dialog"
      aria-label="Keyboard shortcuts"
    >
      <div
        className="bg-neutral-900 border border-neutral-700 rounded-lg shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-neutral-100">Keyboard Shortcuts</h2>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-200 text-xl leading-none px-2"
            aria-label="Close"
          >
            &times;
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {CATEGORY_ORDER.map((category) => {
            const shortcuts = grouped[category];
            if (shortcuts.length === 0) return null;

            return (
              <div key={category}>
                <h3 className="text-sm font-medium text-neutral-400 uppercase tracking-wide mb-2">
                  {category}
                </h3>
                <div className="space-y-1">
                  {shortcuts.map((shortcut) => (
                    <div
                      key={shortcut.id}
                      className="flex items-center justify-between py-1"
                    >
                      <span className="text-sm text-neutral-300">
                        {shortcut.description}
                      </span>
                      <kbd className="text-xs bg-neutral-800 border border-neutral-600 rounded px-1.5 py-0.5 text-neutral-300 font-mono ml-2 whitespace-nowrap">
                        {shortcut.keys}
                      </kbd>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-4 pt-3 border-t border-neutral-700 text-xs text-neutral-500 text-center">
          Press <kbd className="bg-neutral-800 border border-neutral-600 rounded px-1 py-0.5 font-mono">?</kbd> or <kbd className="bg-neutral-800 border border-neutral-600 rounded px-1 py-0.5 font-mono">Esc</kbd> to close
        </div>
      </div>
    </div>
  );
}
