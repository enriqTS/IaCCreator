'use client';

import { useCallback, useRef } from 'react';
import type { Connector, ArchitectureBlock } from '@/types/diagram';
import type { ConnectionSchema, SchemaField } from '@/config/connection-schemas';
import { useDiagramStore } from '@/store/diagram-store';
import { Label } from '@/components/ui/label';
import SchemaFieldRenderer from './SchemaFieldRenderer';

interface ConnectionConfigPanelProps {
  connector: Connector;
  sourceBlock: ArchitectureBlock;
  targetBlock: ArchitectureBlock;
  schema: ConnectionSchema;
}

/** Keys that belong exclusively to the route_handler role */
const ROUTE_HANDLER_KEYS = ['route_path', 'http_method'];
/** Keys that belong exclusively to the authorizer role */
const AUTHORIZER_KEYS = ['authorizer_name', 'payload_format_version'];

export default function ConnectionConfigPanel({
  connector,
  sourceBlock,
  targetBlock,
  schema,
}: ConnectionConfigPanelProps) {
  const updateConnectorConfig = useDiagramStore((s) => s.updateConnectorConfig);
  const removeConnectorConfigKeys = useDiagramStore((s) => s.removeConnectorConfigKeys);

  // Track previous role to detect role changes.
  // Default to 'route_handler' when no role is set (per requirement 3.2).
  const prevRoleRef = useRef<string>(
    (connector.connectionConfig?.connection_role as string) ?? 'route_handler',
  );

  const config = connector.connectionConfig ?? {};

  const handleFieldChange = useCallback(
    (key: string, value: string | number | boolean) => {
      // Handle role change — clear stale fields from previous role
      if (key === 'connection_role') {
        const prevRole = prevRoleRef.current;
        const newRole = value as string;

        if (prevRole !== newRole) {
          if (prevRole === 'route_handler' && newRole === 'authorizer') {
            // Switching to authorizer: remove route_handler-specific keys
            removeConnectorConfigKeys(connector.id, ROUTE_HANDLER_KEYS);
          } else if (prevRole === 'authorizer' && newRole === 'route_handler') {
            // Switching to route_handler: remove authorizer-specific keys
            removeConnectorConfigKeys(connector.id, AUTHORIZER_KEYS);
          }
          prevRoleRef.current = newRole;
        }
      }

      updateConnectorConfig(connector.id, key, value);
    },
    [connector.id, updateConnectorConfig, removeConnectorConfigKeys],
  );

  /** Determine if a field should be visible based on its visibleWhen condition */
  const isFieldVisible = (field: SchemaField): boolean => {
    if (!field.visibleWhen) return true;
    const { field: condField, value: condValue } = field.visibleWhen;
    const currentValue = config[condField] ?? schema.fields.find((f) => f.key === condField)?.defaultValue;
    return currentValue === condValue;
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

      {/* Schema label */}
      <span className="text-xs text-muted-foreground">{schema.label}</span>

      {/* Schema fields */}
      {visibleFields.length > 0 ? (
        <div className="flex flex-col gap-3">
          {visibleFields.map((field) => (
            <SchemaFieldRenderer
              key={field.key}
              field={field}
              value={config[field.key]}
              allValues={config}
              onChange={handleFieldChange}
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
