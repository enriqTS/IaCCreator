import type { ConnectionSchema } from './registry';

export const lambdaDynamodbSchema: ConnectionSchema = {
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
