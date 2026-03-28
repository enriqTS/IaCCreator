'use client';

import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { getSchemas } from '@/store/schema-store';
import type { TerraformVariableSchema, ValidationRule } from '@/types/terraform-variables';
import type { ResourceConfig } from '@/types/diagram';
import KeyValueEditor from './KeyValueEditor';
import ListEditor from './ListEditor';

interface SchemaConfigFormProps {
  elementId: string;
  serviceType: string;
  onValidationChange?: (hasErrors: boolean) => void;
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

export default function SchemaConfigForm({ elementId, serviceType, onValidationChange }: SchemaConfigFormProps) {
  const canvasObject = useDiagramStore((s) => s.canvasObjects.get(elementId));
  const updateCanvasObject = useDiagramStore((s) => s.updateCanvasObject);
  const [errors, setErrors] = useState<Record<string, string>>({});
  // Track which non-General groups the user has explicitly expanded
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  // Track if General has been explicitly collapsed
  const [generalCollapsed, setGeneralCollapsed] = useState(false);

  const schemas = getSchemas();
  const entries = schemas[serviceType] ?? [];

  const block = canvasObject?.objectType === 'architecture-block' ? canvasObject : null;
  const config = block?.config ?? ({} as ResourceConfig);

  // Group entries by group field
  const groups = useMemo(() => {
    const map = new Map<string, TerraformVariableSchema[]>();
    for (const entry of entries) {
      const group = entry.group ?? 'General';
      if (!map.has(group)) map.set(group, []);
      map.get(group)!.push(entry);
    }
    return map;
  }, [entries]);

  // Compute which groups have at least one visible entry
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

  // Notify parent of validation state changes via effect (not during render)
  const onValidationChangeRef = useRef(onValidationChange);
  onValidationChangeRef.current = onValidationChange;
  useEffect(() => {
    onValidationChangeRef.current?.(hasErrors);
  }, [hasErrors]);

  const handleChange = useCallback(
    (entry: TerraformVariableSchema, rawValue: unknown) => {
      let value = rawValue;

      // Coerce types
      if (entry.type === 'number' && typeof rawValue === 'string') {
        value = rawValue === '' ? undefined : Number(rawValue);
      }
      if (entry.type === 'bool' && typeof rawValue !== 'boolean') {
        value = Boolean(rawValue);
      }

      // Validate
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

      // Build the partial update starting with the changed field
      const configUpdate: Record<string, unknown> = { [entry.name]: value };

      // visible_when clearing: when a discriminating field changes, clear dependent
      // fields that become hidden so stale values don't persist in the config.
      for (const dep of entries) {
        if (dep.visible_when && dep.visible_when.field === entry.name) {
          // Evaluate visibility with the NEW value of the discriminating field
          if (value !== dep.visible_when.equals) {
            configUpdate[dep.name] = undefined;
            // Also clear any validation errors for the now-hidden field
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

  const isGroupExpanded = (group: string): boolean => {
    if (group === 'General') return !generalCollapsed;
    return expandedGroups.has(group);
  };

  const toggleGroup = (group: string) => {
    if (group === 'General') {
      setGeneralCollapsed((prev) => !prev);
    } else {
      setExpandedGroups((prev) => {
        const next = new Set(prev);
        if (next.has(group)) next.delete(group);
        else next.add(group);
        return next;
      });
    }
  };

  return (
    <div data-testid="schema-config-form" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {hasErrors && (
        <div data-testid="validation-error-summary" style={{ color: '#f87171', fontSize: '12px', padding: '4px 0' }}>
          ⚠ {Object.keys(errors).length} validation error{Object.keys(errors).length > 1 ? 's' : ''}
        </div>
      )}

      {visibleGroups.map(([group, groupEntries]) => {
        const expanded = isGroupExpanded(group);

        return (
          <div key={group} data-testid={`config-group-${group}`}>
            <button
              data-testid={`group-toggle-${group}`}
              onClick={() => toggleGroup(group)}
              style={groupHeaderStyle}
            >
              <span>{expanded ? '▾' : '▸'} {group}</span>
            </button>

            {expanded && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '8px 0' }}>
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
            )}
          </div>
        );
      })}
    </div>
  );
}

/** Expose helpers for external consumers and testing */
export { validateValue, isVisible };

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
    return (
      <label style={fieldLabelStyle}>
        <span style={labelTextStyle}>{entry.description}</span>
        <select
          data-testid={`field-${entry.name}`}
          value={currentValue !== undefined && currentValue !== null ? String(currentValue) : ''}
          onChange={(e) => {
            // Try to preserve the original type from options
            const opt = entry.options!.find((o) => String(o.value) === e.target.value);
            onChange(entry, opt ? opt.value : e.target.value);
          }}
          style={inputStyle}
        >
          <option value="">Select...</option>
          {entry.options.map((opt) => (
            <option key={String(opt.value)} value={String(opt.value)}>
              {opt.label}
            </option>
          ))}
        </select>
        {error && <span data-testid={`error-${entry.name}`} style={errorStyle}>{error}</span>}
      </label>
    );
  }

  // Bool → checkbox
  if (entry.type === 'bool') {
    return (
      <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', paddingBottom: '2px' }}>
        <input
          data-testid={`field-${entry.name}`}
          type="checkbox"
          checked={currentValue === true}
          onChange={(e) => onChange(entry, e.target.checked)}
        />
        <span style={labelTextStyle}>{entry.description}</span>
      </label>
    );
  }

  // Map → KeyValueEditor
  if (entry.type === 'map') {
    return (
      <div style={fieldLabelStyle}>
        <span style={labelTextStyle}>{entry.description}</span>
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
      <div style={fieldLabelStyle}>
        <span style={labelTextStyle}>{entry.description}</span>
        <ListEditor
          value={currentValue as string[] | undefined}
          onChange={(val) => onChange(entry, val)}
        />
      </div>
    );
  }

  // Number input
  if (entry.type === 'number') {
    return (
      <label style={fieldLabelStyle}>
        <span style={labelTextStyle}>{entry.description}</span>
        <input
          data-testid={`field-${entry.name}`}
          type="number"
          value={currentValue !== undefined && currentValue !== null ? String(currentValue) : ''}
          onChange={(e) => onChange(entry, e.target.value)}
          placeholder={entry.default !== undefined && entry.default !== null ? String(entry.default) : ''}
          min={entry.validation?.min ?? undefined}
          max={entry.validation?.max ?? undefined}
          style={{
            ...inputStyle,
            borderColor: error ? '#dc2626' : 'rgba(255,255,255,0.2)',
          }}
        />
        {error && <span data-testid={`error-${entry.name}`} style={errorStyle}>{error}</span>}
      </label>
    );
  }

  // Default: text input
  return (
    <label style={fieldLabelStyle}>
      <span style={labelTextStyle}>{entry.description}</span>
      <input
        data-testid={`field-${entry.name}`}
        type="text"
        value={currentValue !== undefined && currentValue !== null ? String(currentValue) : ''}
        onChange={(e) => onChange(entry, e.target.value)}
        placeholder={entry.default !== undefined && entry.default !== null ? String(entry.default) : ''}
        style={{
          ...inputStyle,
          borderColor: error ? '#dc2626' : 'rgba(255,255,255,0.2)',
        }}
      />
      {error && <span data-testid={`error-${entry.name}`} style={errorStyle}>{error}</span>}
    </label>
  );
}

// --- Styles ---

const groupHeaderStyle: React.CSSProperties = {
  background: 'none',
  border: 'none',
  color: 'rgba(255,255,255,0.8)',
  fontSize: '13px',
  fontWeight: 600,
  cursor: 'pointer',
  padding: '4px 0',
  textAlign: 'left',
  width: '100%',
};

const fieldLabelStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '4px',
  fontSize: '13px',
};

const labelTextStyle: React.CSSProperties = {
  color: 'rgba(255,255,255,0.6)',
  fontSize: '12px',
};

const inputStyle: React.CSSProperties = {
  backgroundColor: '#2a2a2a',
  color: '#fff',
  border: '1px solid rgba(255,255,255,0.2)',
  borderRadius: '4px',
  padding: '4px 8px',
  fontSize: '13px',
  width: '100%',
  boxSizing: 'border-box',
};

const errorStyle: React.CSSProperties = {
  color: '#f87171',
  fontSize: '11px',
};
