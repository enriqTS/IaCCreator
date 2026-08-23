'use client';

import { useCallback, useMemo, useState } from 'react';
import type { SchemaField } from '@/connections';
import LinkedEntryFieldRenderer from './LinkedEntryFieldRenderer';
import type { ArchitectureBlock } from '@/types/diagram';
import { useDiagramStore } from '@/store/diagram-store';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Check, X, Plus, Route } from 'lucide-react';

export interface LinkedSelectFieldRendererProps {
  field: SchemaField;
  value: string | undefined;
  allValues: Record<string, string | number | boolean>;
  onChange: (key: string, value: string | number | boolean) => void;
  /** The source block to read linked config from */
  sourceBlock: ArchitectureBlock;
  /** The target block (used for createTemplate interpolation) */
  targetBlock: ArchitectureBlock;
  /** Connector ID for atomic sync operations */
  connectorId: string;
}

/**
 * Renders a linkedSelect field that sources its options from a connected block's
 * config array and supports inline creation of new entries with atomic sync.
 */
export default function LinkedSelectFieldRenderer({
  field,
  value,
  allValues: _allValues,
  onChange,
  sourceBlock,
  targetBlock,
  connectorId,
}: LinkedSelectFieldRendererProps) {
  const [isCreating, setIsCreating] = useState(false);
  const [newValue, setNewValue] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [newEntryFields, setNewEntryFields] = useState<Record<string, unknown>>({});

  const createLinkedEntry = useDiagramStore((s) => s.createLinkedEntry);
  const updateLinkedEntry = useDiagramStore((s) => s.updateLinkedEntry);

  // Read options from source block's config at the linkedConfigPath
  const entryFields = useMemo(() => field.linkedEntryFields ?? [], [field.linkedEntryFields]);
  const configPath = field.linkedConfigPath ?? '';
  const displayKey = field.displayKey ?? '';
  const sourceArray = (sourceBlock.config as Record<string, unknown>)?.[configPath] as
    | Record<string, unknown>[]
    | undefined;

  const options = Array.isArray(sourceArray)
    ? sourceArray
        .map((entry) => String(entry[displayKey] ?? ''))
        .filter((v) => v.length > 0)
    : [];

  const handleSelectChange = useCallback(
    (val: string) => {
      if (val === '__create_new__') {
        setIsCreating(true);
        setNewValue('');
        setValidationError(null);
        setNewEntryFields(
          Object.fromEntries(
            entryFields
              .filter((f) => f.defaultValue !== undefined)
              .map((f) => [f.key, f.defaultValue]),
          ),
        );
      } else {
        onChange(field.key, val);
      }
    },
    [field.key, onChange, entryFields],
  );

  const validateInput = useCallback(
    (input: string): string | null => {
      if (!input.trim()) {
        return 'Value is required';
      }
      if (field.validation?.pattern && !field.validation.pattern.test(input)) {
        return field.validation.errorMessage ?? 'Invalid value';
      }
      if (field.validation?.maxLength && input.length > field.validation.maxLength) {
        return `Maximum ${field.validation.maxLength} characters`;
      }
      return null;
    },
    [field.validation],
  );

  const handleConfirmCreate = useCallback(() => {
    const error = validateInput(newValue);
    if (error) {
      setValidationError(error);
      return;
    }

    // Build the new entry from createTemplate
    const template = { ...(field.createTemplate ?? {}) };
    if (displayKey) {
      template[displayKey] = newValue;
    }
    // The schema names the keys that bind an entry to the connected resource
    if (field.targetNameKey) {
      template[field.targetNameKey] = targetBlock.name;
    }
    if (field.targetIdKey) {
      template[field.targetIdKey] = targetBlock.id;
    }
    // Whatever the user chose for the schema's per-entry fields
    Object.assign(template, newEntryFields);

    createLinkedEntry(
      sourceBlock.id,
      configPath,
      template,
      connectorId,
      field.key,
      newValue,
    );

    setIsCreating(false);
    setNewValue('');
    setValidationError(null);
  }, [
    newValue,
    validateInput,
    field.createTemplate,
    field.key,
    displayKey,
    field.targetNameKey,
    field.targetIdKey,
    targetBlock.name,
    targetBlock.id,
    newEntryFields,
    sourceBlock.id,
    configPath,
    connectorId,
    createLinkedEntry,
  ]);

  const handleCancelCreate = useCallback(() => {
    setIsCreating(false);
    setNewValue('');
    setValidationError(null);
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleConfirmCreate();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        handleCancelCreate();
      }
    },
    [handleConfirmCreate, handleCancelCreate],
  );

  // Entries belonging to this connection, matched by id where one was recorded
  const connectedRoutes = useMemo(() => {
    if (!Array.isArray(sourceArray)) return [];
    const idKey = field.targetIdKey;
    const nameKey = field.targetNameKey;
    return sourceArray.filter((entry) =>
      idKey && entry[idKey]
        ? entry[idKey] === targetBlock.id
        : nameKey
          ? String(entry[nameKey] ?? '') === targetBlock.name
          : false,
    );
  }, [sourceArray, field.targetIdKey, field.targetNameKey, targetBlock.id, targetBlock.name]);

  // Inline create mode
  if (isCreating) {
    return (
      <div className="flex flex-col gap-1.5">
        <Label className="text-xs text-muted-foreground">{field.label}</Label>
        <div className="flex items-center gap-1">
          <Input
            data-testid={`field-${field.key}-create`}
            type="text"
            value={newValue}
            onChange={(e) => {
              setNewValue(e.target.value);
              setValidationError(null);
            }}
            onKeyDown={handleKeyDown}
            placeholder={field.placeholder ?? `New ${field.label.toLowerCase()}...`}
            maxLength={field.validation?.maxLength}
            aria-invalid={validationError ? true : undefined}
            autoFocus
            className="flex-1"
          />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0"
            onClick={handleConfirmCreate}
            aria-label="Confirm"
          >
            <Check className="h-4 w-4" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0"
            onClick={handleCancelCreate}
            aria-label="Cancel"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
        {entryFields.map((entryField) => (
          <LinkedEntryFieldRenderer
            key={entryField.key}
            field={entryField}
            value={newEntryFields[entryField.key]}
            onChange={(next) =>
              setNewEntryFields((prev) => ({ ...prev, [entryField.key]: next }))
            }
            testIdSuffix="create"
          />
        ))}
        {validationError && (
          <span data-testid={`error-${field.key}`} className="text-destructive text-xs">
            {validationError}
          </span>
        )}
      </div>
    );
  }

  // Normal select mode
  return (
    <div className="flex flex-col gap-1.5">
      <Label className="text-xs text-muted-foreground">{field.label}</Label>
      <Select
        value={value ?? ''}
        onValueChange={handleSelectChange}
      >
        <SelectTrigger
          data-testid={`field-${field.key}`}
          className="w-full"
        >
          <SelectValue placeholder={field.placeholder ?? `Select ${field.label.toLowerCase()}...`} />
        </SelectTrigger>
        <SelectContent>
          {options.map((opt) => (
            <SelectItem key={opt} value={opt}>
              {opt}
            </SelectItem>
          ))}
          <SelectItem value="__create_new__">
            <span className="flex items-center gap-1">
              <Plus className="h-3 w-3" />
              Create new...
            </span>
          </SelectItem>
        </SelectContent>
      </Select>

      {/* Routes on this connection — read-only list of all routes targeting this Lambda */}
      {connectedRoutes.length > 0 && (
        <div data-testid="connected-routes-list" className="mt-2 flex flex-col gap-1">
          <div className="flex items-center gap-1.5">
            <Route className="h-3 w-3 text-muted-foreground" />
            <span className="text-xs font-medium text-muted-foreground">
              Routes on this connection ({connectedRoutes.length})
            </span>
          </div>
          <ul className="flex flex-col gap-2 pl-4">
            {connectedRoutes.map((entry, idx) => {
              const path = String(entry[displayKey] ?? '');
              return (
                <li key={`${path}-${idx}`} className="flex flex-col gap-1">
                  <span
                    className="text-xs text-foreground/80 font-mono truncate"
                    title={path}
                  >
                    {path}
                  </span>
                  {entryFields.map((entryField) => (
                    <LinkedEntryFieldRenderer
                      key={entryField.key}
                      field={entryField}
                      value={entry[entryField.key]}
                      onChange={(next) =>
                        updateLinkedEntry(
                          sourceBlock.id,
                          configPath,
                          displayKey,
                          path,
                          entryField.key,
                          next,
                        )
                      }
                      compact
                      testIdSuffix={path}
                    />
                  ))}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
