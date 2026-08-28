/**
 * Shared types for connection schemas.
 *
 * The schemas themselves are served by the backend — see `schema-store.ts`.
 */

import type { ServiceType } from '@/types/diagram';

/** Field types supported by the schema renderer */
export type SchemaFieldType = 'text' | 'number' | 'select' | 'radio' | 'multiSelect' | 'linkedSelect';

/** A single configurable field in a connection schema */
export interface SchemaField {
  key: string;
  label: string;
  type: SchemaFieldType;
  defaultValue?: string | number | boolean;
  options?: { value: string; label: string }[];
  placeholder?: string;
  validation?: {
    required?: boolean;
    pattern?: RegExp;
    min?: number;
    max?: number;
    maxLength?: number;
    errorMessage?: string;
  };
  /** Show this field only when another field has a specific value */
  visibleWhen?: { field: string; value: string | number | boolean };

  // --- multiSelect properties ---
  /** Values that are mutually exclusive with all others (e.g., ["ANY"]) */
  multiSelectExclusive?: string[];

  // --- linkedSelect properties ---
  /** Dot-path to the array field on the source block's config (e.g., "routes") */
  linkedConfigPath?: string;
  /** Property name within each array entry to display as option label (e.g., "path") */
  displayKey?: string;
  /** Template key that receives the connected resource's name */
  targetNameKey?: string;
  /** Template key that receives the connected resource's stable id */
  targetIdKey?: string;
  /** Fields the editor may change on an existing linked entry */
  linkedEntryFields?: LinkedEntryField[];
}

/** One editable field of a linked entry, rendered inline in the entry list */
export interface LinkedEntryField {
  key: string;
  label: string;
  type: SchemaFieldType;
  defaultValue?: string | number | boolean | string[];
  options?: { value: string; label: string }[];
  /** Values that cannot be combined with any other, such as the ANY method */
  exclusiveOptions?: string[];
}

/** Schema for one kind of connection between two services */
export interface ConnectionSchema {
  sourcePair: [ServiceType, ServiceType];
  connectionType: string;
  label: string;
  isDefault: boolean;
  regionPolicy: 'same-region' | 'cross-region';
  fields: SchemaField[];
}
