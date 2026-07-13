import type { ConnectionSchema } from './registry';

export const lambdaS3Schema: ConnectionSchema = {
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
