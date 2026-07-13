/**
 * Connection Schema Registry
 *
 * Central registry file containing shared types and the CONNECTION_SCHEMA_REGISTRY Map.
 * Each individual schema is imported from its own sibling file.
 */

import type { ServiceType } from '@/types/diagram';

import { apiGatewayLambdaSchema } from './apigw-lambda';
import { sqsLambdaSchema } from './sqs-lambda';
import { lambdaDynamodbSchema } from './lambda-dynamodb';
import { lambdaS3Schema } from './lambda-s3';
import { lambdaSnsSchema } from './lambda-sns';
import { lambdaSqsSchema } from './lambda-sqs';
import { snsLambdaSchema } from './sns-lambda';
import { snsSqsSchema } from './sns-sqs';
import { lambdaCloudwatchSchema } from './lambda-cloudwatch';

// --- Shared Types ---

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
  /** Template object for creating new entries (displayKey is overwritten with user input) */
  createTemplate?: Record<string, unknown>;
}

/** Schema for a specific service pair */
export interface ConnectionSchema {
  sourcePair: [ServiceType, ServiceType];
  label: string;
  fields: SchemaField[];
  /** Function to generate the line label from connectionConfig */
  getLabel: (config: Record<string, string | number | boolean>) => string | null;
  /** Whether this connection type uses dashed stroke */
  getDashed?: (config: Record<string, string | number | boolean>) => boolean;
}

/** Registry key is "sourceType::targetType" */
export type SchemaRegistryKey = `${ServiceType}::${ServiceType}`;

// --- Registry ---

export const CONNECTION_SCHEMA_REGISTRY = new Map<SchemaRegistryKey, ConnectionSchema>([
  ['api-gateway::lambda', apiGatewayLambdaSchema],
  ['sqs::lambda', sqsLambdaSchema],
  ['lambda::dynamodb', lambdaDynamodbSchema],
  ['lambda::s3', lambdaS3Schema],
  ['lambda::sns', lambdaSnsSchema],
  ['lambda::sqs', lambdaSqsSchema],
  ['sns::lambda', snsLambdaSchema],
  ['sns::sqs', snsSqsSchema],
  ['lambda::cloudwatch', lambdaCloudwatchSchema],
]);
