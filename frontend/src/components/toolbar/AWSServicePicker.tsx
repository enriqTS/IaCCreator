'use client';

import { useState, useRef, useEffect } from 'react';
import { AWS_ICON_REGISTRY } from '@/data/aws-icon-registry';
import { useDiagramStore } from '@/store/diagram-store';

export default function AWSServicePicker() {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(new Set());
  const setActiveTool = useDiagramStore((s) => s.setActiveTool);
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

  const lowerSearch = search.toLowerCase();

  const filteredCategories = AWS_ICON_REGISTRY.map((cat) => ({
    ...cat,
    services: cat.services.filter((s) => s.name.toLowerCase().includes(lowerSearch)),
  })).filter((cat) => cat.services.length > 0);

  const toggleCategory = (name: string) => {
    setCollapsedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  return (
    <div ref={containerRef} style={{ position: 'relative' }}>
      <button
        data-testid="aws-service-picker-button"
        title="Add Service"
        onClick={() => { setOpen((v) => !v); setSearch(''); }}
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
          fontWeight: 'bold',
          background: open ? 'rgba(59, 130, 246, 0.3)' : 'transparent',
          color: '#e5e5e5',
          transition: 'background 0.15s',
        }}
        onMouseEnter={(e) => {
          if (!open) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = open ? 'rgba(59, 130, 246, 0.3)' : 'transparent';
        }}
      >
        +
      </button>

      {open && (
        <div
          data-testid="aws-service-picker-dropdown"
          style={{
            position: 'absolute',
            top: 44,
            left: '50%',
            transform: 'translateX(-50%)',
            width: 280,
            maxHeight: 400,
            overflowY: 'auto',
            background: '#1e1e1e',
            borderRadius: 10,
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.6)',
            border: '1px solid #333',
            zIndex: 100,
            padding: '8px 0',
          }}
        >
          {/* Search input */}
          <div style={{ padding: '4px 8px 8px' }}>
            <input
              data-testid="aws-service-picker-search"
              type="text"
              placeholder="Search services..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              autoFocus
              style={{
                width: '100%',
                padding: '6px 10px',
                borderRadius: 6,
                border: '1px solid #444',
                background: '#2a2a2a',
                color: '#e5e5e5',
                fontSize: 13,
                outline: 'none',
                boxSizing: 'border-box',
              }}
            />
          </div>

          {/* Categories */}
          {filteredCategories.length === 0 && (
            <div style={{ padding: '12px 16px', color: '#888', fontSize: 13 }}>
              No services found
            </div>
          )}

          {filteredCategories.map((cat) => {
            const isCollapsed = collapsedCategories.has(cat.name);
            return (
              <div key={cat.name}>
                <button
                  onClick={() => toggleCategory(cat.name)}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: '6px 12px',
                    background: 'transparent',
                    border: 'none',
                    color: '#aaa',
                    fontSize: 11,
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                >
                  <span style={{ fontSize: 9 }}>{isCollapsed ? '▶' : '▼'}</span>
                  {cat.name}
                </button>

                {!isCollapsed &&
                  cat.services.map((svc) => {
                    const supported = svc.serviceType !== null;
                    return (
                      <button
                        key={svc.iconPath}
                        data-testid={`service-item-${svc.name}`}
                        disabled={!supported}
                        onClick={() => {
                          if (supported && svc.serviceType) {
                            setActiveTool({ type: 'place-service', serviceType: svc.serviceType });
                            setOpen(false);
                          }
                        }}
                        style={{
                          width: '100%',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                          padding: '5px 16px',
                          background: 'transparent',
                          border: 'none',
                          color: '#e5e5e5',
                          fontSize: 13,
                          cursor: supported ? 'pointer' : 'default',
                          opacity: supported ? 1 : 0.4,
                          textAlign: 'left',
                        }}
                        onMouseEnter={(e) => {
                          if (supported) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = 'transparent';
                        }}
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={svc.iconPath}
                          alt={svc.name}
                          width={16}
                          height={16}
                          style={{ flexShrink: 0 }}
                        />
                        {svc.name}
                      </button>
                    );
                  })}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
