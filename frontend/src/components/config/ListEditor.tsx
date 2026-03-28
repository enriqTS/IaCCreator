'use client';

import { useState } from 'react';

interface ListEditorProps {
  value: string[] | undefined;
  onChange: (value: string[]) => void;
  description?: string;
}

export default function ListEditor({ value, onChange, description }: ListEditorProps) {
  const items = value ?? [];
  const [newItem, setNewItem] = useState('');

  const handleAdd = () => {
    const trimmed = newItem.trim();
    if (!trimmed) return;
    onChange([...items, trimmed]);
    setNewItem('');
  };

  const handleRemove = (index: number) => {
    onChange(items.filter((_, i) => i !== index));
  };

  const handleChange = (index: number, val: string) => {
    const next = [...items];
    next[index] = val;
    onChange(next);
  };

  return (
    <div data-testid="list-editor" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      {description && (
        <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '11px' }}>{description}</span>
      )}

      {items.map((item, i) => (
        <div key={i} style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
          <input
            data-testid={`list-item-${i}`}
            type="text"
            value={item}
            onChange={(e) => handleChange(i, e.target.value)}
            style={{ ...listInputStyle, flex: 1 }}
          />
          <button
            data-testid={`list-remove-${i}`}
            onClick={() => handleRemove(i)}
            style={removeButtonStyle}
            title="Remove"
          >
            ×
          </button>
        </div>
      ))}

      {/* Add new item row */}
      <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
        <input
          data-testid="list-new-item"
          type="text"
          value={newItem}
          onChange={(e) => setNewItem(e.target.value)}
          placeholder="Add item..."
          style={{ ...listInputStyle, flex: 1 }}
          onKeyDown={(e) => { if (e.key === 'Enter') handleAdd(); }}
        />
        <button
          data-testid="list-add-btn"
          onClick={handleAdd}
          style={addButtonStyle}
          title="Add"
        >
          +
        </button>
      </div>
    </div>
  );
}

const listInputStyle: React.CSSProperties = {
  backgroundColor: '#2a2a2a',
  color: '#fff',
  border: '1px solid rgba(255,255,255,0.2)',
  borderRadius: '4px',
  padding: '3px 6px',
  fontSize: '12px',
};

const removeButtonStyle: React.CSSProperties = {
  backgroundColor: 'transparent',
  color: '#f87171',
  border: '1px solid rgba(255,255,255,0.15)',
  borderRadius: '4px',
  padding: '2px 6px',
  fontSize: '14px',
  cursor: 'pointer',
  lineHeight: 1,
};

const addButtonStyle: React.CSSProperties = {
  backgroundColor: 'transparent',
  color: '#60a5fa',
  border: '1px solid rgba(255,255,255,0.15)',
  borderRadius: '4px',
  padding: '2px 6px',
  fontSize: '14px',
  cursor: 'pointer',
  lineHeight: 1,
};
