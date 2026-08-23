'use client';

import type { LinkedEntryField } from '@/connections';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { toggleExclusiveSelection } from './schema-field-utils';

export interface LinkedEntryFieldRendererProps {
  field: LinkedEntryField;
  value: unknown;
  onChange: (value: unknown) => void;
  /** Rendered without its own label when the caller already labels the row */
  compact?: boolean;
  testIdSuffix: string;
}

/** Read a stored entry value as a list, tolerating the comma-separated legacy form. */
function asList(value: unknown, fallback: unknown): string[] {
  const raw = value ?? fallback;
  if (Array.isArray(raw)) return raw.map(String);
  if (typeof raw === 'string' && raw.length > 0) return raw.split(',').filter(Boolean);
  return [];
}

/**
 * Renders one editable field of a linked entry — the schema decides which fields
 * exist and what values they allow, so nothing about a service is declared here.
 */
export default function LinkedEntryFieldRenderer({
  field,
  value,
  onChange,
  compact = false,
  testIdSuffix,
}: LinkedEntryFieldRendererProps) {
  const options = field.options ?? [];

  if (field.type === 'multiSelect') {
    const selected = asList(value, field.defaultValue);
    const handleToggle = (toggled: string) => {
      const next = toggleExclusiveSelection(
        selected,
        toggled,
        field.exclusiveOptions ?? [],
        options.map((opt) => opt.value),
      );
      // An entry with no values selected would generate nothing, so keep the last one
      if (next.length > 0) onChange(next);
    };

    return (
      <div className="flex flex-col gap-1">
        {!compact && <Label className="text-xs text-muted-foreground">{field.label}</Label>}
        <div
          className="flex flex-wrap gap-1"
          role="group"
          aria-label={field.label}
          data-testid={`entry-field-${field.key}-${testIdSuffix}`}
        >
          {options.map((option) => {
            const isSelected = selected.includes(option.value);
            return (
              <Button
                key={option.value}
                type="button"
                variant={isSelected ? 'default' : 'outline'}
                size="sm"
                className="h-6 px-2 text-[11px]"
                onClick={() => handleToggle(option.value)}
                aria-pressed={isSelected}
                data-testid={`entry-option-${field.key}-${option.value}-${testIdSuffix}`}
              >
                {option.label}
              </Button>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      {!compact && <Label className="text-xs text-muted-foreground">{field.label}</Label>}
      <Input
        data-testid={`entry-field-${field.key}-${testIdSuffix}`}
        type={field.type === 'number' ? 'number' : 'text'}
        value={value === undefined || value === null ? '' : String(value)}
        onChange={(e) => onChange(e.target.value)}
        className="h-7 text-xs"
      />
    </div>
  );
}
