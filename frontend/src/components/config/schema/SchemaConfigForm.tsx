'use client';

import { useState, useMemo, useCallback, useEffect, useRef, type ReactNode } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { getSchemas } from '@/store/schema-store';
import type { TerraformVariableSchema, ValidationRule } from '@/types/terraform-variables';
import type { ResourceConfig } from '@/types/diagram';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import KeyValueEditor from '../editors/KeyValueEditor';
import ListEditor from '../editors/ListEditor';
import ConfigTabs, { type ConfigTab } from '../overlay/ConfigTabs';
import FieldLabel from './FieldLabel';
import ValidationSummary, { type ValidationIssue } from './ValidationSummary';

interface SchemaConfigFormProps {
  elementId: string;
  serviceType: string;
  onValidationChange?: (hasErrors: boolean) => void;
  /** Appended after the schema's own group tabs, so the strip stays flat. */
  extraTabs?: ConfigTab[];
  /** Rendered above the first group's fields, for configuration outside the schema. */
  leadingFields?: ReactNode;
}

/** Evaluate a visible_when condition against the current config. */
function isVisible(entry: TerraformVariableSchema, config: ResourceConfig): boolean {
  if (!entry.visible_when) return true;
  const { field, equals } = entry.visible_when;
  const currentValue = (config as Record<string, unknown>)[field];
  return currentValue === equals;
}

/** Validate a value against a ValidationRule. Returns error message or null. */
function validateValue(
  value: unknown,
  validation: ValidationRule | null | undefined,
  entry: TerraformVariableSchema,
): string | null {
  if (!validation) return null;
  if (value === undefined || value === null || value === '') return null;

  if (validation.allowed_values && validation.allowed_values.length > 0) {
    const numVal = typeof value === 'string' ? Number(value) : value;
    const match = validation.allowed_values.some((av) => av === value || av === numVal);
    if (!match) {
      return `Value must be one of the allowed values`;
    }
  }

  if (entry.type === 'number' && (validation.min !== undefined && validation.min !== null || validation.max !== undefined && validation.max !== null)) {
    const num = typeof value === 'string' ? Number(value) : (value as number);
    if (isNaN(num)) return 'Value must be a number';
    if (validation.min !== undefined && validation.min !== null && num < validation.min) {
      return `Value must be at least ${validation.min}`;
    }
    if (validation.max !== undefined && validation.max !== null && num > validation.max) {
      return `Value must be at most ${validation.max}`;
    }
  }

  if (validation.pattern) {
    const str = String(value);
    try {
      const re = new RegExp(validation.pattern);
      if (!re.test(str)) {
        return validation.pattern_description ?? `Value must match pattern: ${validation.pattern}`;
      }
    } catch {
      // invalid regex in schema — skip
    }
  }

  return null;
}

export default function SchemaConfigForm({ elementId, serviceType, onValidationChange, extraTabs = [], leadingFields }: SchemaConfigFormProps) {
  const canvasObject = useDiagramStore((s) => s.canvasObjects.get(elementId));
  const updateCanvasObject = useDiagramStore((s) => s.updateCanvasObject);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [openTab, setOpenTab] = useState('');
  const pendingFocusRef = useRef<string | null>(null);

  const schemas = getSchemas();
  const entries = useMemo(() => schemas[serviceType] ?? [], [schemas, serviceType]);

  const block = canvasObject?.objectType === 'architecture-block' ? canvasObject : null;
  const config = useMemo(() => block?.config ?? ({} as ResourceConfig), [block?.config]);

  const groups = useMemo(() => {
    const map = new Map<string, TerraformVariableSchema[]>();
    for (const entry of entries) {
      const group = entry.group ?? 'General';
      if (!map.has(group)) map.set(group, []);
      map.get(group)!.push(entry);
    }
    return map;
  }, [entries]);

  const visibleGroups = useMemo(() => {
    const result: [string, TerraformVariableSchema[]][] = [];
    for (const [group, groupEntries] of groups) {
      const visibleEntries = groupEntries.filter((e) => isVisible(e, config));
      if (visibleEntries.length > 0) {
        result.push([group, visibleEntries]);
      }
    }
    return result;
  }, [groups, config]);

  const hasErrors = Object.keys(errors).length > 0;

  const issues = useMemo<ValidationIssue[]>(() => {
    const result: ValidationIssue[] = [];
    for (const [group, groupEntries] of visibleGroups) {
      for (const entry of groupEntries) {
        if (errors[entry.name]) {
          result.push({ key: entry.name, label: entry.label || entry.name, group });
        }
      }
    }
    return result;
  }, [visibleGroups, errors]);

  // Runs after every render so the field is focused once its tab has opened
  useEffect(() => {
    const target = pendingFocusRef.current;
    if (!target) return;
    pendingFocusRef.current = null;
    document.getElementById(fieldId(target))?.focus();
  });

  const onValidationChangeRef = useRef(onValidationChange);
  useEffect(() => {
    onValidationChangeRef.current = onValidationChange;
  });
  useEffect(() => {
    onValidationChangeRef.current?.(hasErrors);
  }, [hasErrors]);

  const handleChange = useCallback(
    (entry: TerraformVariableSchema, rawValue: unknown) => {
      let value = rawValue;

      if (entry.type === 'number' && typeof rawValue === 'string') {
        value = rawValue === '' ? undefined : Number(rawValue);
      }
      if (entry.type === 'bool' && typeof rawValue !== 'boolean') {
        value = Boolean(rawValue);
      }

      const error = validateValue(value, entry.validation, entry);
      setErrors((prev) => {
        const next = { ...prev };
        if (error) {
          next[entry.name] = error;
        } else {
          delete next[entry.name];
        }
        return next;
      });

      const configUpdate: Record<string, unknown> = { [entry.name]: value };

      for (const dep of entries) {
        if (dep.visible_when && dep.visible_when.field === entry.name) {
          if (value !== dep.visible_when.equals) {
            configUpdate[dep.name] = undefined;
            setErrors((prev) => {
              if (!(dep.name in prev)) return prev;
              const next = { ...prev };
              delete next[dep.name];
              return next;
            });
          }
        }
      }

      updateCanvasObject(elementId, { config: { ...config, ...configUpdate } } as Partial<import('@/types/diagram').CanvasObject>);
    },
    [elementId, updateCanvasObject, entries, config],
  );

  if (!block) return null;

  return (
    <div data-testid="schema-config-form" className="flex min-w-0 flex-col gap-3">
      <ValidationSummary
        issues={issues}
        onSelect={(issue) => {
          setOpenTab(issue.group);
          pendingFocusRef.current = issue.key;
        }}
      />

      <ConfigTabs
        testIdPrefix="schema"
        value={openTab}
        onValueChange={setOpenTab}
        tabs={[
          ...visibleGroups.map(([group, groupEntries], groupIndex) => ({
            id: group,
            label: group,
            status: groupEntries.some((entry) => errors[entry.name])
              ? ('error' as const)
              : undefined,
            content: (
              <div data-testid={`config-group-${group}`} className="flex flex-col gap-3 py-2">
                {groupIndex === 0 && leadingFields}
                {groupEntries.map((entry) => (
                  <FieldRenderer
                    key={entry.name}
                    entry={entry}
                    config={config}
                    error={errors[entry.name]}
                    onChange={handleChange}
                  />
                ))}
              </div>
            ),
          })),
          ...extraTabs,
        ]}
      />
    </div>
  );
}

/** Expose helpers for external consumers and testing */
export { validateValue, isVisible };

/** The DOM id of a field's control, so its label and the summary can reach it. */
function fieldId(name: string): string {
  return `config-field-${name}`;
}

// --- Field Renderer ---

function FieldRenderer({
  entry,
  config,
  error,
  onChange,
}: {
  entry: TerraformVariableSchema;
  config: ResourceConfig;
  error?: string;
  onChange: (entry: TerraformVariableSchema, value: unknown) => void;
}) {
  const currentValue = (config as Record<string, unknown>)[entry.name];

  // Select dropdown when options are defined
  if (entry.options && entry.options.length > 0) {
    const hasGroups = entry.options.some((o) => o.group);

    // Group options by their group field for sectioned rendering
    const groupedOptions = hasGroups
      ? entry.options.reduce<Map<string, typeof entry.options>>((map, opt) => {
          const g = opt.group ?? 'Other';
          if (!map.has(g)) map.set(g, []);
          map.get(g)!.push(opt);
          return map;
        }, new Map())
      : null;

    return (
      <div className="flex flex-col gap-1.5">
        <FieldLabel
          label={entry.label || entry.name}
          description={entry.description}
          required={entry.required}
          htmlFor={fieldId(entry.name)}
        />
        <Select
          value={currentValue !== undefined && currentValue !== null ? String(currentValue) : ''}
          onValueChange={(val) => {
            const opt = entry.options!.find((o) => String(o.value) === val);
            onChange(entry, opt ? opt.value : val);
          }}
        >
          <SelectTrigger id={fieldId(entry.name)} data-testid={`field-${entry.name}`} className="w-full">
            <SelectValue placeholder="Select..." />
          </SelectTrigger>
          <SelectContent>
            {groupedOptions
              ? Array.from(groupedOptions.entries()).map(([groupName, opts]) => (
                  <SelectGroup key={groupName}>
                    <SelectLabel>{groupName}</SelectLabel>
                    {opts.map((opt) => (
                      <SelectItem key={String(opt.value)} value={String(opt.value)}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                ))
              : entry.options.map((opt) => (
                  <SelectItem key={String(opt.value)} value={String(opt.value)}>
                    {opt.label}
                  </SelectItem>
                ))}
          </SelectContent>
        </Select>
        {error && <span data-testid={`error-${entry.name}`} className="text-destructive text-xs">{error}</span>}
      </div>
    );
  }

  // Bool → checkbox
  if (entry.type === 'bool') {
    return (
      <div className="flex items-center gap-2">
        <Checkbox
          data-testid={`field-${entry.name}`}
          checked={currentValue === true}
          onCheckedChange={(checked) => onChange(entry, checked === true)}
        />
        <FieldLabel
          label={entry.label || entry.name}
          description={entry.description}
          required={entry.required}
          htmlFor={fieldId(entry.name)}
        />
      </div>
    );
  }

  // Map → KeyValueEditor
  if (entry.type === 'map') {
    return (
      <div className="flex flex-col gap-1.5">
        <FieldLabel
          label={entry.label || entry.name}
          description={entry.description}
          required={entry.required}
          htmlFor={fieldId(entry.name)}
        />
        <KeyValueEditor
          value={currentValue as Record<string, string> | undefined}
          onChange={(val) => onChange(entry, val)}
        />
      </div>
    );
  }

  // List → ListEditor
  if (entry.type === 'list') {
    return (
      <div className="flex flex-col gap-1.5">
        <FieldLabel
          label={entry.label || entry.name}
          description={entry.description}
          required={entry.required}
          htmlFor={fieldId(entry.name)}
        />
        <ListEditor
          value={currentValue as string[] | undefined}
          onChange={(val) => onChange(entry, val)}
        />
      </div>
    );
  }

  // Number input — use type="text" with inputMode="numeric" to avoid browser spinner arrows
  if (entry.type === 'number') {
    return (
      <div className="flex flex-col gap-1.5">
        <FieldLabel
          label={entry.label || entry.name}
          description={entry.description}
          required={entry.required}
          htmlFor={fieldId(entry.name)}
        />
        <Input
          id={fieldId(entry.name)}
          data-testid={`field-${entry.name}`}
          type="text"
          inputMode="numeric"
          value={currentValue !== undefined && currentValue !== null ? String(currentValue) : ''}
          onChange={(e) => onChange(entry, e.target.value)}
          placeholder={entry.default !== undefined && entry.default !== null ? String(entry.default) : ''}
          aria-invalid={error ? true : undefined}
        />
        {error && <span data-testid={`error-${entry.name}`} className="text-destructive text-xs">{error}</span>}
      </div>
    );
  }

  // Default: text input
  return (
    <div className="flex flex-col gap-1.5">
      <FieldLabel
        label={entry.label || entry.name}
        description={entry.description}
        required={entry.required}
        htmlFor={fieldId(entry.name)}
      />
      <Input
        id={fieldId(entry.name)}
        data-testid={`field-${entry.name}`}
        type="text"
        value={currentValue !== undefined && currentValue !== null ? String(currentValue) : ''}
        onChange={(e) => onChange(entry, e.target.value)}
        placeholder={entry.default !== undefined && entry.default !== null ? String(entry.default) : ''}
        aria-invalid={error ? true : undefined}
      />
      {error && <span data-testid={`error-${entry.name}`} className="text-destructive text-xs">{error}</span>}
    </div>
  );
}
