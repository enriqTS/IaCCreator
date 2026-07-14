'use client';

import { useCallback, useState } from 'react';
import type { SchemaField } from '@/connections';
import type { ArchitectureBlock } from '@/types/diagram';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { isFieldVisible, validateField } from './schema-field-utils';
import MultiSelectFieldRenderer from './MultiSelectFieldRenderer';
import LinkedSelectFieldRenderer from './LinkedSelectFieldRenderer';

export { isFieldVisible, validateField } from './schema-field-utils';

export interface SchemaFieldRendererProps {
  field: SchemaField;
  value: string | number | boolean | undefined;
  /** Current values of all fields — used for visibleWhen evaluation */
  allValues: Record<string, string | number | boolean>;
  onChange: (key: string, value: string | number | boolean) => void;
  /** The source block of the connection (used by linkedSelect) */
  sourceBlock?: ArchitectureBlock;
  /** The target block of the connection (used by linkedSelect) */
  targetBlock?: ArchitectureBlock;
  /** The connector ID (used by linkedSelect for atomic sync) */
  connectorId?: string;
}

/**
 * Renders a single schema field based on its type definition.
 * Handles text, number, select, and radio field types with validation
 * and conditional visibility (visibleWhen).
 */
export default function SchemaFieldRenderer({
  field,
  value,
  allValues,
  onChange,
  sourceBlock,
  targetBlock,
  connectorId,
}: SchemaFieldRendererProps) {
  const [touched, setTouched] = useState(false);

  // Evaluate visibility
  if (!isFieldVisible(field, allValues)) {
    return null;
  }

  const error = touched ? validateField(field, value) : null;

  const handleBlur = useCallback(() => {
    setTouched(true);
  }, []);

  // --- Radio field ---
  if (field.type === 'radio') {
    return (
      <RadioFieldRenderer
        field={field}
        value={value}
        onChange={onChange}
      />
    );
  }

  // --- MultiSelect field ---
  if (field.type === 'multiSelect') {
    return (
      <MultiSelectFieldRenderer
        field={field}
        value={value as string | undefined}
        allValues={allValues}
        onChange={onChange}
      />
    );
  }

  // --- LinkedSelect field ---
  if (field.type === 'linkedSelect') {
    if (!sourceBlock || !targetBlock || !connectorId) {
      return null;
    }
    return (
      <LinkedSelectFieldRenderer
        field={field}
        value={value as string | undefined}
        allValues={allValues}
        onChange={onChange}
        sourceBlock={sourceBlock}
        targetBlock={targetBlock}
        connectorId={connectorId}
      />
    );
  }

  // --- Select field ---
  if (field.type === 'select') {
    return (
      <SelectFieldRenderer
        field={field}
        value={value}
        error={error}
        onChange={onChange}
        onBlur={handleBlur}
      />
    );
  }

  // --- Number field ---
  if (field.type === 'number') {
    return (
      <NumberFieldRenderer
        field={field}
        value={value}
        error={error}
        onChange={onChange}
        onBlur={handleBlur}
      />
    );
  }

  // --- Text field (default) ---
  return (
    <TextFieldRenderer
      field={field}
      value={value}
      error={error}
      onChange={onChange}
      onBlur={handleBlur}
    />
  );
}

// --- Sub-renderers ---

function RadioFieldRenderer({
  field,
  value,
  onChange,
}: {
  field: SchemaField;
  value: string | number | boolean | undefined;
  onChange: (key: string, value: string | number | boolean) => void;
}) {
  const currentValue = value !== undefined ? String(value) : (field.defaultValue !== undefined ? String(field.defaultValue) : '');

  return (
    <div className="flex flex-col gap-2">
      <Label className="text-xs text-muted-foreground">{field.label}</Label>
      <RadioGroup
        data-testid={`field-${field.key}`}
        value={currentValue}
        onValueChange={(val) => onChange(field.key, val)}
      >
        {field.options?.map((option) => (
          <div key={option.value} className="flex items-center gap-2">
            <RadioGroupItem
              value={option.value}
              id={`${field.key}-${option.value}`}
            />
            <Label
              htmlFor={`${field.key}-${option.value}`}
              className="text-sm font-normal cursor-pointer"
            >
              {option.label}
            </Label>
          </div>
        ))}
      </RadioGroup>
    </div>
  );
}

function SelectFieldRenderer({
  field,
  value,
  error,
  onChange,
  onBlur,
}: {
  field: SchemaField;
  value: string | number | boolean | undefined;
  error: string | null;
  onChange: (key: string, value: string | number | boolean) => void;
  onBlur: () => void;
}) {
  const currentValue = value !== undefined && value !== null ? String(value) : (field.defaultValue !== undefined ? String(field.defaultValue) : '');

  return (
    <div className="flex flex-col gap-1.5">
      <Label className="text-xs text-muted-foreground">{field.label}</Label>
      <Select
        value={currentValue}
        onValueChange={(val) => {
          onChange(field.key, val);
          onBlur();
        }}
      >
        <SelectTrigger
          data-testid={`field-${field.key}`}
          className="w-full"
          aria-invalid={error ? true : undefined}
        >
          <SelectValue placeholder={field.placeholder ?? 'Select...'} />
        </SelectTrigger>
        <SelectContent>
          {field.options?.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {error && (
        <span data-testid={`error-${field.key}`} className="text-destructive text-xs">
          {error}
        </span>
      )}
    </div>
  );
}

function NumberFieldRenderer({
  field,
  value,
  error,
  onChange,
  onBlur,
}: {
  field: SchemaField;
  value: string | number | boolean | undefined;
  error: string | null;
  onChange: (key: string, value: string | number | boolean) => void;
  onBlur: () => void;
}) {
  const displayValue = value !== undefined && value !== null ? String(value) : '';

  return (
    <div className="flex flex-col gap-1.5">
      <Label className="text-xs text-muted-foreground">{field.label}</Label>
      <Input
        data-testid={`field-${field.key}`}
        type="text"
        inputMode="numeric"
        value={displayValue}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === '') {
            onChange(field.key, '' as unknown as string);
          } else {
            const num = Number(raw);
            if (!isNaN(num)) {
              onChange(field.key, num);
            }
          }
        }}
        onBlur={onBlur}
        placeholder={field.placeholder ?? (field.defaultValue !== undefined ? String(field.defaultValue) : '')}
        aria-invalid={error ? true : undefined}
      />
      {error && (
        <span data-testid={`error-${field.key}`} className="text-destructive text-xs">
          {error}
        </span>
      )}
    </div>
  );
}

function TextFieldRenderer({
  field,
  value,
  error,
  onChange,
  onBlur,
}: {
  field: SchemaField;
  value: string | number | boolean | undefined;
  error: string | null;
  onChange: (key: string, value: string | number | boolean) => void;
  onBlur: () => void;
}) {
  const displayValue = value !== undefined && value !== null ? String(value) : '';

  return (
    <div className="flex flex-col gap-1.5">
      <Label className="text-xs text-muted-foreground">{field.label}</Label>
      <Input
        data-testid={`field-${field.key}`}
        type="text"
        value={displayValue}
        onChange={(e) => onChange(field.key, e.target.value)}
        onBlur={onBlur}
        placeholder={field.placeholder ?? (field.defaultValue !== undefined ? String(field.defaultValue) : '')}
        maxLength={field.validation?.maxLength}
        aria-invalid={error ? true : undefined}
      />
      {error && (
        <span data-testid={`error-${field.key}`} className="text-destructive text-xs">
          {error}
        </span>
      )}
    </div>
  );
}
