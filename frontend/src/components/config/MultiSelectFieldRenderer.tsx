'use client';

import { useMemo } from 'react';
import type { SchemaField } from '@/config/connection-schemas';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

export interface MultiSelectFieldRendererProps {
  field: SchemaField;
  value: string | number | boolean | undefined;
  allValues: Record<string, string | number | boolean>;
  onChange: (key: string, value: string) => void;
}

/**
 * Renders a multi-select field as a group of toggleable buttons.
 * Supports exclusive option logic (e.g., "ANY" deselects all others).
 * Stores value as a comma-separated string ordered by schema options list.
 */
export default function MultiSelectFieldRenderer({
  field,
  value,
  allValues: _allValues,
  onChange,
}: MultiSelectFieldRendererProps) {
  const options = field.options ?? [];
  const exclusiveValues = new Set(field.multiSelectExclusive ?? []);

  // Parse the current value into a Set of selected values
  const selectedValues = useMemo(() => {
    const rawValue = value !== undefined && value !== null && value !== ''
      ? String(value)
      : (field.defaultValue !== undefined ? String(field.defaultValue) : '');

    if (!rawValue) return new Set<string>();
    return new Set(rawValue.split(',').filter(Boolean));
  }, [value, field.defaultValue]);

  // Serialize selected values as comma-separated string ordered by schema options
  const serialize = (selected: Set<string>): string => {
    return options
      .map((opt) => opt.value)
      .filter((v) => selected.has(v))
      .join(',');
  };

  const handleToggle = (toggledValue: string) => {
    const newSelected = new Set(selectedValues);

    if (newSelected.has(toggledValue)) {
      // Deselecting a value
      newSelected.delete(toggledValue);
    } else {
      // Selecting a value
      if (exclusiveValues.has(toggledValue)) {
        // Toggling an exclusive value: deselect all others
        newSelected.clear();
        newSelected.add(toggledValue);
      } else {
        // Toggling a non-exclusive value: deselect any exclusive values
        for (const excl of exclusiveValues) {
          newSelected.delete(excl);
        }
        newSelected.add(toggledValue);
      }
    }

    onChange(field.key, serialize(newSelected));
  };

  // Validation: show error if no values are selected
  const isEmpty = selectedValues.size === 0;

  return (
    <div className="flex flex-col gap-1.5">
      <Label className="text-xs text-muted-foreground">{field.label}</Label>
      <div
        className="flex flex-wrap gap-1.5"
        role="group"
        aria-label={field.label}
        data-testid={`field-${field.key}`}
      >
        {options.map((option) => {
          const isSelected = selectedValues.has(option.value);
          return (
            <Button
              key={option.value}
              type="button"
              variant={isSelected ? 'default' : 'outline'}
              size="sm"
              className={cn(
                'transition-colors',
                isSelected && 'shadow-sm',
              )}
              onClick={() => handleToggle(option.value)}
              aria-pressed={isSelected}
              data-testid={`multiselect-option-${option.value}`}
            >
              {option.label}
            </Button>
          );
        })}
      </div>
      {isEmpty && (
        <span
          data-testid={`error-${field.key}`}
          className="text-destructive text-xs"
          role="alert"
        >
          At least one method must be selected
        </span>
      )}
    </div>
  );
}
