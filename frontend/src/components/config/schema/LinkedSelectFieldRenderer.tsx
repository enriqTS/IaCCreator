'use client';

import { useCallback, useMemo, useState } from 'react';
import type { SchemaField } from '@/connections';
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
  allValues,
  onChange,
  sourceBlock,
  targetBlock,
  connectorId,
}: LinkedSelectFieldRendererProps) {
  const [isCreating, setIsCreating] = useState(false);
  const [newValue, setNewValue] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);

  const createLinkedEntry = useDiagramStore((s) => s.createLinkedEntry);

  // Read options from source block's config at the linkedConfigPath
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
      } else {
        onChange(field.key, val);
      }
    },
    [field.key, onChange],
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
    // Set integration_name to target block's name
    if ('integration_name' in template) {
      template.integration_name = targetBlock.name;
    }
    // Set method from current allValues if available
    if ('method' in template && allValues.http_method) {
      template.method = allValues.http_method;
    }

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
    targetBlock.name,
    allValues,
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

  // Compute routes belonging to this connection (matching target block's name)
  const connectedRoutes = useMemo(() => {
    if (!Array.isArray(sourceArray)) return [];
    return sourceArray.filter(
      (entry) => String(entry.integration_name ?? '') === targetBlock.name,
    );
  }, [sourceArray, targetBlock.name]);

  // Format methods display for a route entry
  const formatRouteMethods = (entry: Record<string, unknown>): string => {
    const methods = entry.methods;
    if (Array.isArray(methods)) {
      return (methods as string[]).join(', ');
    }
    return 'ANY';
  };

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
          <ul className="flex flex-col gap-0.5 pl-4">
            {connectedRoutes.map((entry, idx) => {
              const path = String(entry[displayKey] ?? '');
              const methods = formatRouteMethods(entry);
              const label = `${methods} ${path}`;
              const truncated = label.length > 40 ? label.slice(0, 37) + '...' : label;
              return (
                <li
                  key={`${path}-${idx}`}
                  className="text-xs text-foreground/80 font-mono truncate"
                  title={label}
                >
                  {truncated}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
