'use client';

import { useState } from 'react';

interface KeyValueEditorProps {
  value: Record<string, string> | undefined;
  onChange: (value: Record<string, string>) => void;
  description?: string;
}

export default function KeyValueEditor({ value, onChange, description }: KeyValueEditorProps) {
  const entries = Object.entries(value ?? {});
  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');
  const [keyError, setKeyError] = useState('');

  const handleAdd = () => {
    const trimmedKey = newKey.trim();
    if (!trimmedKey) {
      setKeyError('Key cannot be empty');
      return;
    }
    if (value && trimmedKey in value) {
      setKeyError('Key already exists');
      return;
    }
    setKeyError('');
    onChange({ ...(value ?? {}), [trimmedKey]: newValue });
    setNewKey('');
    setNewValue('');
  };

  const handleRemove = (key: string) => {
    const next = { ...(value ?? {}) };
    delete next[key];
    onChange(next);
  };

  const handleValueChange = (key: string, val: string) => {
    onChange({ ...(value ?? {}), [key]: val });
  };

  return (
    <div data-testid="key-value-editor" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      {description && (
        <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '11px' }}>{description}</span>
      )}

      {entries.map(([k, v]) => (
        <div key={k} style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
          <input
            data-testid={`kv-key-${k}`}
            type="text"
            value={k}
            readOnly
            style={{ ...kvInputStyle, width: '100px', opacity: 0.7 }}
          />
          <input
            data-testid={`kv-value-${k}`}
            type="text"
            value={v}
            onChange={(e) => handleValueChange(k, e.target.value)}
            style={{ ...kvInputStyle, flex: 1 }}
          />
          <button
            data-testid={`kv-remove-${k}`}
            onClick={() => handleRemove(k)}
            style={removeButtonStyle}
            title="Remove"
          >
            ×
          </button>
        </div>
      ))}

      {/* Add new entry row */}
      <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
        <input
          data-testid="kv-new-key"
          type="text"
          value={newKey}
          onChange={(e) => { setNewKey(e.target.value); setKeyError(''); }}
          placeholder="Key"
          style={{ ...kvInputStyle, width: '100px' }}
        />
        <input
          data-testid="kv-new-value"
          type="text"
          value={newValue}
          onChange={(e) => setNewValue(e.target.value)}
          placeholder="Value"
          style={{ ...kvInputStyle, flex: 1 }}
        />
        <button
          data-testid="kv-add-btn"
          onClick={handleAdd}
          style={addButtonStyle}
          title="Add"
        >
          +
        </button>
      </div>
      {keyError && (
        <span data-testid="kv-key-error" style={{ color: '#f87171', fontSize: '11px' }}>{keyError}</span>
      )}
    </div>
  );
}

const kvInputStyle: React.CSSProperties = {
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
