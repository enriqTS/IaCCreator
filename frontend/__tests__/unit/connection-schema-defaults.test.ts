import { afterEach, expect, it } from 'vitest';
import {
  clearConnectionSchemaCache,
  getConnectionSchema,
  hydrateConnectionSchemas,
} from '@/connections/schema-store';

afterEach(clearConnectionSchemaCache);

it('exposes backend list defaults in the multi-select renderer format', () => {
  hydrateConnectionSchemas([{
    source: 's3',
    target: 'sqs',
    connection_type: 'notifies',
    label: 'S3 → SQS',
    is_default: true,
    region_policy: 'same-region',
    fields: [{
      key: 'events',
      label: 'Events',
      type: 'multiSelect',
      required: false,
      default: ['s3:ObjectCreated:*', 's3:ObjectRemoved:*'],
    }],
  }]);
  expect(getConnectionSchema('s3', 'sqs')?.fields[0].defaultValue)
    .toBe('s3:ObjectCreated:*,s3:ObjectRemoved:*');
});
