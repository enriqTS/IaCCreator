'use client';

import { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

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
    <div data-testid="key-value-editor" className="flex flex-col gap-1.5">
      {description && (
        <span className="text-xs text-muted-foreground">{description}</span>
      )}

      {entries.map(([k, v]) => (
        <div key={k} className="flex gap-1 items-center">
          <Input
            data-testid={`kv-key-${k}`}
            type="text"
            value={k}
            readOnly
            className="w-24 opacity-70"
          />
          <Input
            data-testid={`kv-value-${k}`}
            type="text"
            value={v}
            onChange={(e) => handleValueChange(k, e.target.value)}
            className="flex-1"
          />
          <Button
            data-testid={`kv-remove-${k}`}
            variant="ghost"
            size="icon"
            onClick={() => handleRemove(k)}
            title="Remove"
            className="text-destructive shrink-0 h-8 w-8"
          >
            ×
          </Button>
        </div>
      ))}

      <div className="flex gap-1 items-center">
        <Input
          data-testid="kv-new-key"
          type="text"
          value={newKey}
          onChange={(e) => { setNewKey(e.target.value); setKeyError(''); }}
          placeholder="Key"
          className="w-24"
        />
        <Input
          data-testid="kv-new-value"
          type="text"
          value={newValue}
          onChange={(e) => setNewValue(e.target.value)}
          placeholder="Value"
          className="flex-1"
        />
        <Button
          data-testid="kv-add-btn"
          variant="ghost"
          size="icon"
          onClick={handleAdd}
          title="Add"
          className="text-primary shrink-0 h-8 w-8"
        >
          +
        </Button>
      </div>
      {keyError && (
        <span data-testid="kv-key-error" className="text-destructive text-xs">{keyError}</span>
      )}
    </div>
  );
}
