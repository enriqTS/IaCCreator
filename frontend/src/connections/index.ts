/**
 * Connections domain module barrel export.
 */

export type { SchemaFieldType, SchemaField, ConnectionSchema, LinkedEntryField } from './registry';

export {
  fetchConnectionSchemas,
  getConnectionSchema,
  getDefaultConnectionType,
  hasConnectionPair,
  clearConnectionSchemaCache,
} from './schema-store';

export { getPresentation, CONNECTION_PRESENTATION } from './presentation';
export type { ConnectionPresentation, ConnectionConfigValues } from './presentation';

export { findConnectorForLine, getSchemaForConnector, ensureConnectorForLine, resolveConnectionForPair } from './connector-utils';
export type { ResolvedConnection } from './connector-utils';
