'use client';

import { useCallback } from 'react';
import type { Connector, ArchitectureBlock } from '@/types/diagram';
import type { ConnectionSchema, SchemaField } from './registry';
import { useDiagramStore } from '@/store/diagram-store';
import { Label } from '@/components/ui/label';
import SchemaFieldRenderer from '@/components/config/schema/SchemaFieldRenderer';
import { getConnectionSchemasForPair } from './schema-store';

interface ConnectionConfigPanelProps {
  connector: Connector;
  sourceBlock: ArchitectureBlock;
  targetBlock: ArchitectureBlock;
  schema: ConnectionSchema;
}

export default function ConnectionConfigPanel({
  connector,
  sourceBlock,
  targetBlock,
  schema,
}: ConnectionConfigPanelProps) {
  const updateConnectorConfig = useDiagramStore((s) => s.updateConnectorConfig);
  const removeConnectorConfigKeys = useDiagramStore((s) => s.removeConnectorConfigKeys);
  const updateConnectorType = useDiagramStore((s) => s.updateConnectorType);

  const config = connector.connectionConfig ?? {};

  // Build allValues with defaults applied — ensures visibleWhen conditions work
  // even when the connectionConfig is empty (e.g., freshly created connector)
  const allValues: Record<string, string | number | boolean> = {};
  for (const field of schema.fields) {
    if (field.defaultValue !== undefined) {
      allValues[field.key] = field.defaultValue;
    }
  }
  // Overlay actual config values on top of defaults
  Object.assign(allValues, config);

  const handleFieldChange = useCallback(
    (key: string, value: string | number | boolean) => {
      updateConnectorConfig(connector.id, key, value);
    },
    [connector.id, updateConnectorConfig],
  );

  // A pair may offer several kinds of connection; switching drops the previous kind's keys
  const alternatives = getConnectionSchemasForPair(
    sourceBlock.serviceType,
    targetBlock.serviceType,
  );

  const handleTypeChange = useCallback(
    (nextType: string) => {
      const next = alternatives.find((s) => s.connectionType === nextType);
      if (!next) return;
      const keep = new Set(next.fields.map((f) => f.key));
      const stale = Object.keys(connector.connectionConfig ?? {}).filter(
        (key) => !keep.has(key),
      );
      if (stale.length > 0) {
        removeConnectorConfigKeys(connector.id, stale);
      }
      updateConnectorType(connector.id, nextType);
    },
    [alternatives, connector.id, connector.connectionConfig, removeConnectorConfigKeys, updateConnectorType],
  );

  /** Determine if a field should be visible based on its visibleWhen condition */
  const isFieldVisible = (field: SchemaField): boolean => {
    if (!field.visibleWhen) return true;
    const { field: condField, value: condValue } = field.visibleWhen;
    return allValues[condField] === condValue;
  };

  const visibleFields = schema.fields.filter(isFieldVisible);

  return (
    <div data-testid="connection-config-panel" className="flex flex-col gap-4">
      {/* Header: source → target */}
      <div className="flex items-center gap-2">
        <Label className="text-sm font-semibold text-foreground">
          {sourceBlock.name}
        </Label>
        <span className="text-muted-foreground text-sm">→</span>
        <Label className="text-sm font-semibold text-foreground">
          {targetBlock.name}
        </Label>
      </div>

      {/* Connection kind — only shown when the pair offers more than one */}
      {alternatives.length > 1 ? (
        <div className="flex flex-col gap-1">
          <Label className="text-xs text-muted-foreground">Connection type</Label>
          <select
            data-testid="connection-type-select"
            className="border-input bg-background h-8 rounded-md border px-2 text-sm"
            value={schema.connectionType}
            onChange={(e) => handleTypeChange(e.target.value)}
          >
            {alternatives.map((option) => (
              <option key={option.connectionType} value={option.connectionType}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      ) : (
        <span className="text-xs text-muted-foreground">{schema.label}</span>
      )}

      {/* Schema fields */}
      {visibleFields.length > 0 ? (
        <div className="flex flex-col gap-3">
          {visibleFields.map((field) => (
            <SchemaFieldRenderer
              key={field.key}
              field={field}
              value={allValues[field.key]}
              allValues={allValues}
              onChange={handleFieldChange}
              sourceBlock={sourceBlock}
              targetBlock={targetBlock}
              connectorId={connector.id}
            />
          ))}
        </div>
      ) : (
        <span className="text-xs text-muted-foreground">
          No additional configuration available for this connection type.
        </span>
      )}
    </div>
  );
}
