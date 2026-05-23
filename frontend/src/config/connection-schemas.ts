/**
 * Connection Schema Registry
 *
 * Defines the configurable fields for each supported service pair connection.
 * The registry maps "sourceType::targetType" keys to ConnectionSchema objects
 * that drive the ConnectionConfigPanel UI and line label rendering.
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

// --- Schema Definitions ---

const apiGatewayLambdaSchema: ConnectionSchema = {
  sourcePair: ['api-gateway', 'lambda'],
  label: 'API Gateway → Lambda',
  fields: [
    {
      key: 'connection_role',
      label: 'Role',
      type: 'radio',
      defaultValue: 'route_handler',
      options: [
        { value: 'route_handler', label: 'Route Handler' },
        { value: 'authorizer', label: 'Authorizer' },
      ],
    },
    {
      key: 'http_method',
      label: 'HTTP Methods',
      type: 'multiSelect',
      defaultValue: 'ANY',
      options: [
        { value: 'GET', label: 'GET' },
        { value: 'POST', label: 'POST' },
        { value: 'PUT', label: 'PUT' },
        { value: 'DELETE', label: 'DELETE' },
        { value: 'PATCH', label: 'PATCH' },
        { value: 'OPTIONS', label: 'OPTIONS' },
        { value: 'HEAD', label: 'HEAD' },
        { value: 'ANY', label: 'ANY' },
      ],
      multiSelectExclusive: ['ANY'],
      visibleWhen: { field: 'connection_role', value: 'route_handler' },
    },
    {
      key: 'route_path',
      label: 'Route',
      type: 'linkedSelect',
      linkedConfigPath: 'routes',
      displayKey: 'path',
      createTemplate: { method: 'ANY', path: '', integration_name: '' },
      validation: {
        required: true,
        pattern: /^\/[\w\-/{}\$]*$/,
        maxLength: 128,
        errorMessage: 'Must start with / and contain only alphanumeric, /, -, _, {, }, $',
      },
      visibleWhen: { field: 'connection_role', value: 'route_handler' },
    },
    {
      key: 'authorizer_name',
      label: 'Authorizer Name',
      type: 'text',
      validation: {
        required: true,
        pattern: /^[\w\-]+$/,
        maxLength: 128,
        errorMessage: 'Only alphanumeric, hyphens, and underscores (1-128 chars)',
      },
      visibleWhen: { field: 'connection_role', value: 'authorizer' },
    },
    {
      key: 'payload_format_version',
      label: 'Payload Format Version',
      type: 'select',
      defaultValue: '2.0',
      options: [
        { value: '1.0', label: '1.0' },
        { value: '2.0', label: '2.0' },
      ],
      visibleWhen: { field: 'connection_role', value: 'authorizer' },
    },
  ],
  getLabel: (config) => {
    const role = config.connection_role as string;
    if (role === 'authorizer') {
      const name = config.authorizer_name || 'auth';
      return `Authorizer: ${name}`;
    }
    if (role === 'route_handler' || !role) {
      const methods = config.http_method || 'ANY';
      const path = config.route_path || '/$default';
      const label = `${methods} ${path}`;
      return label.length > 30 ? label.slice(0, 27) + '...' : label;
    }
    return null;
  },
  getDashed: (config) => config.connection_role === 'authorizer',
};

const sqsLambdaSchema: ConnectionSchema = {
  sourcePair: ['sqs', 'lambda'],
  label: 'SQS → Lambda',
  fields: [
    {
      key: 'batch_size',
      label: 'Batch Size',
      type: 'number',
      defaultValue: 10,
      validation: { min: 1, max: 10000, errorMessage: 'Must be between 1 and 10000' },
    },
    {
      key: 'maximum_batching_window_in_seconds',
      label: 'Batching Window (seconds)',
      type: 'number',
      placeholder: 'Optional (0-300)',
      validation: { min: 0, max: 300, errorMessage: 'Must be between 0 and 300' },
    },
  ],
  getLabel: (config) => {
    const batch = config.batch_size || 10;
    return `Event Source (batch: ${batch})`;
  },
};

const lambdaDynamodbSchema: ConnectionSchema = {
  sourcePair: ['lambda', 'dynamodb'],
  label: 'Lambda → DynamoDB',
  fields: [
    {
      key: 'access_pattern',
      label: 'Access Pattern',
      type: 'select',
      defaultValue: 'full',
      options: [
        { value: 'read', label: 'Read Only (GetItem, Query, Scan)' },
        { value: 'write', label: 'Write Only (PutItem, UpdateItem, DeleteItem)' },
        { value: 'full', label: 'Full Access (Read + Write)' },
      ],
    },
  ],
  getLabel: (config) => {
    const pattern = config.access_pattern as string;
    if (pattern === 'read') return 'Read Only';
    if (pattern === 'write') return 'Write Only';
    return 'Read/Write';
  },
};

const lambdaS3Schema: ConnectionSchema = {
  sourcePair: ['lambda', 's3'],
  label: 'Lambda → S3',
  fields: [
    {
      key: 'access_pattern',
      label: 'Access Pattern',
      type: 'select',
      defaultValue: 'full',
      options: [
        { value: 'read', label: 'Read Only (GetObject, ListBucket)' },
        { value: 'write', label: 'Write Only (PutObject, DeleteObject)' },
        { value: 'full', label: 'Full Access (Read + Write)' },
      ],
    },
  ],
  getLabel: (config) => {
    const pattern = config.access_pattern as string;
    if (pattern === 'read') return 'Read Only';
    if (pattern === 'write') return 'Write Only';
    return 'Read/Write';
  },
};

const lambdaSnsSchema: ConnectionSchema = {
  sourcePair: ['lambda', 'sns'],
  label: 'Lambda → SNS',
  fields: [],
  getLabel: () => 'Publish',
};

const lambdaSqsSchema: ConnectionSchema = {
  sourcePair: ['lambda', 'sqs'],
  label: 'Lambda → SQS',
  fields: [],
  getLabel: () => 'Send Message',
};

const snsLambdaSchema: ConnectionSchema = {
  sourcePair: ['sns', 'lambda'],
  label: 'SNS → Lambda',
  fields: [],
  getLabel: () => 'Subscription',
};

const snsSqsSchema: ConnectionSchema = {
  sourcePair: ['sns', 'sqs'],
  label: 'SNS → SQS',
  fields: [],
  getLabel: () => 'Subscription',
};

const lambdaCloudwatchSchema: ConnectionSchema = {
  sourcePair: ['lambda', 'cloudwatch'],
  label: 'Lambda → CloudWatch',
  fields: [],
  getLabel: () => 'Logging',
};

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
