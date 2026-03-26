'use client';

import { useState, useRef, useEffect } from 'react';

export interface HamburgerMenuProps {
  onNewDiagram: () => void;
  onSave: () => void;
  onLoad: () => void;
  onExport: () => void;
  onProjectSettings: () => void;
}

const MENU_ITEMS: { label: string; action: keyof Omit<HamburgerMenuProps, never> }[] = [
  { label: 'New Diagram', action: 'onNewDiagram' },
  { label: 'Save', action: 'onSave' },
  { label: 'Load', action: 'onLoad' },
  { label: 'Export to Terraform', action: 'onExport' },
  { label: 'Project Settings', action: 'onProjectSettings' },
];

export default function HamburgerMenu(props: HamburgerMenuProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  return (
    <div
      ref={containerRef}
      data-testid="hamburger-menu"
      style={{ position: 'fixed', top: 16, left: 16, zIndex: 50 }}
    >
      <button
        data-testid="hamburger-button"
        onClick={() => setOpen((v) => !v)}
        aria-label="Menu"
        aria-expanded={open}
        style={{
          width: 36,
          height: 36,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: 8,
          border: 'none',
          cursor: 'pointer',
          fontSize: 20,
          background: open ? 'rgba(59, 130, 246, 0.3)' : '#1e1e1e',
          color: '#e5e5e5',
          boxShadow: '0 4px 24px rgba(0, 0, 0, 0.5)',
          transition: 'background 0.15s',
        }}
        onMouseEnter={(e) => {
          if (!open) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = open
            ? 'rgba(59, 130, 246, 0.3)'
            : '#1e1e1e';
        }}
      >
        ☰
      </button>

      {open && (
        <div
          data-testid="hamburger-dropdown"
          style={{
            position: 'absolute',
            top: 44,
            left: 0,
            minWidth: 200,
            background: '#1e1e1e',
            borderRadius: 8,
            padding: '4px 0',
            boxShadow: '0 4px 24px rgba(0, 0, 0, 0.5)',
          }}
        >
          {MENU_ITEMS.map((item) => (
            <button
              key={item.action}
              data-testid={`menu-item-${item.action}`}
              onClick={() => {
                props[item.action]();
                setOpen(false);
              }}
              style={{
                display: 'block',
                width: '100%',
                padding: '8px 16px',
                background: 'transparent',
                border: 'none',
                color: '#e5e5e5',
                fontSize: 14,
                textAlign: 'left',
                cursor: 'pointer',
                transition: 'background 0.15s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
