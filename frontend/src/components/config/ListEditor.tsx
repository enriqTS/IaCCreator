'use client';

import { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

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
    <div data-testid="list-editor" className="flex flex-col gap-1.5">
      {description && (
        <span className="text-xs text-muted-foreground">{description}</span>
      )}

      {items.map((item, i) => (
        <div key={i} className="flex gap-1 items-center">
          <Input
            data-testid={`list-item-${i}`}
            type="text"
            value={item}
            onChange={(e) => handleChange(i, e.target.value)}
            className="flex-1"
          />
          <Button
            data-testid={`list-remove-${i}`}
            variant="ghost"
            size="icon"
            onClick={() => handleRemove(i)}
            title="Remove"
            className="text-destructive shrink-0 h-8 w-8"
          >
            ×
          </Button>
        </div>
      ))}

      <div className="flex gap-1 items-center">
        <Input
          data-testid="list-new-item"
          type="text"
          value={newItem}
          onChange={(e) => setNewItem(e.target.value)}
          placeholder="Add item..."
          className="flex-1"
          onKeyDown={(e) => { if (e.key === 'Enter') handleAdd(); }}
        />
        <Button
          data-testid="list-add-btn"
          variant="ghost"
          size="icon"
          onClick={handleAdd}
          title="Add"
          className="text-primary shrink-0 h-8 w-8"
        >
          +
        </Button>
      </div>
    </div>
  );
}
