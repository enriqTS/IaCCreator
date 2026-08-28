/**
 * Connection schema store — fetches the connection catalog from the backend,
 * maps it to the shape the field renderer expects, and caches it in memory.
 *
 * The backend is the only source of truth for which connections exist and what
 * they can be configured with; nothing here declares those facts.
 */

import type { ServiceType } from '@/types/diagram';
import type { ConnectionSchema, LinkedEntryField, SchemaField, SchemaFieldType } from './registry';

interface ApiOption {
  value: string | number | boolean;
  label: string;
}

interface ApiValidation {
  min?: number | null;
  max?: number | null;
  pattern?: string | null;
  pattern_description?: string | null;
  allowed_values?: (string | number | boolean)[] | null;
}

interface ApiLinkedEntryField {
  key: string;
  label: string;
  type: SchemaFieldType;
  default?: string | number | boolean | string[] | null;
  options?: ApiOption[] | null;
  exclusive_options?: string[] | null;
}

interface ApiLinked {
  config_path: string;
  display_key: string;
  target_name_key?: string | null;
  target_id_key?: string | null;
  entry_fields?: ApiLinkedEntryField[] | null;
}

interface ApiField {
  key: string;
  label: string;
  type: SchemaFieldType;
  required: boolean;
  default?: string | number | boolean | null;
  placeholder?: string | null;
  options?: ApiOption[] | null;
  validation?: ApiValidation | null;
  visible_when?: { field: string; equals: string | number | boolean } | null;
  linked?: ApiLinked | null;
}

export interface ApiConnection {
  source: ServiceType;
  target: ServiceType;
  connection_type: string;
  label: string;
  is_default: boolean;
  region_policy: 'same-region' | 'cross-region';
  fields: ApiField[];
}

/** Key is "source::target::connectionType". */
export type CatalogKey = `${ServiceType}::${ServiceType}::${string}`;

let catalog: Map<CatalogKey, ConnectionSchema> | null = null;

function toEntryField(field: ApiLinkedEntryField): LinkedEntryField {
  return {
    key: field.key,
    label: field.label,
    type: field.type,
    ...(field.default !== null && field.default !== undefined
      ? { defaultValue: field.default }
      : {}),
    ...(field.options
      ? { options: field.options.map((o) => ({ value: String(o.value), label: o.label })) }
      : {}),
    ...(field.exclusive_options ? { exclusiveOptions: field.exclusive_options } : {}),
  };
}

function toField(field: ApiField): SchemaField {
  const validation = field.validation ?? undefined;
  return {
    key: field.key,
    label: field.label,
    type: field.type,
    ...(field.default !== null && field.default !== undefined
      ? { defaultValue: field.default }
      : {}),
    ...(field.placeholder ? { placeholder: field.placeholder } : {}),
    ...(field.options
      ? { options: field.options.map((o) => ({ value: String(o.value), label: o.label })) }
      : {}),
    ...(validation
      ? {
          validation: {
            ...(field.required ? { required: true } : {}),
            ...(validation.min !== null && validation.min !== undefined
              ? { min: validation.min }
              : {}),
            ...(validation.max !== null && validation.max !== undefined
              ? { max: validation.max }
              : {}),
            ...(validation.pattern ? { pattern: new RegExp(validation.pattern) } : {}),
            ...(validation.pattern_description
              ? { errorMessage: validation.pattern_description }
              : {}),
          },
        }
      : field.required
        ? { validation: { required: true } }
        : {}),
    ...(field.visible_when
      ? { visibleWhen: { field: field.visible_when.field, value: field.visible_when.equals } }
      : {}),
    ...(field.linked
      ? {
          linkedConfigPath: field.linked.config_path,
          displayKey: field.linked.display_key,
          ...(field.linked.target_name_key
            ? { targetNameKey: field.linked.target_name_key }
            : {}),
          ...(field.linked.target_id_key
            ? { targetIdKey: field.linked.target_id_key }
            : {}),
          ...(field.linked.entry_fields && field.linked.entry_fields.length > 0
            ? { linkedEntryFields: field.linked.entry_fields.map(toEntryField) }
            : {}),
        }
      : {}),
  };
}

function toSchema(connection: ApiConnection): ConnectionSchema {
  return {
    sourcePair: [connection.source, connection.target],
    connectionType: connection.connection_type,
    label: connection.label,
    isDefault: connection.is_default,
    regionPolicy: connection.region_policy,
    fields: connection.fields.map(toField),
  };
}

export function hydrateConnectionSchemas(connections: ApiConnection[]): void {
  catalog = new Map(
    connections.map((connection) => [
      `${connection.source}::${connection.target}::${connection.connection_type}` as CatalogKey,
      toSchema(connection),
    ]),
  );
}

/** Fetch the catalog once and cache it. Returns false when the backend is unreachable. */
export async function fetchConnectionSchemas(): Promise<boolean> {
  if (catalog) return true;
  try {
    const res = await fetch('/api/connection-schemas');
    if (!res.ok) throw new Error(`Connection schema fetch failed: ${res.status}`);
    const body: { connections: ApiConnection[] } = await res.json();
    hydrateConnectionSchemas(body.connections);
    return true;
  } catch {
    console.warn('Could not load connection schemas; connections stay unconfigured.');
    return false;
  }
}

/** Look up a connection schema, falling back to the pair's default connection type. */
export function getConnectionSchema(
  source: ServiceType,
  target: ServiceType,
  connectionType?: string,
): ConnectionSchema | null {
  if (!catalog) return null;
  if (connectionType) {
    const exact = catalog.get(`${source}::${target}::${connectionType}`);
    if (exact) return exact;
  }
  for (const schema of catalog.values()) {
    if (schema.sourcePair[0] === source && schema.sourcePair[1] === target && schema.isDefault) {
      return schema;
    }
  }
  return null;
}

/** Every connection kind offered for a service pair, in catalog order. */
export function getConnectionSchemasForPair(
  source: ServiceType,
  target: ServiceType,
): ConnectionSchema[] {
  if (!catalog) return [];
  return [...catalog.values()].filter(
    (schema) => schema.sourcePair[0] === source && schema.sourcePair[1] === target,
  );
}

/** Clear the cached catalog (used by tests). */
export function clearConnectionSchemaCache(): void {
  catalog = null;
}
