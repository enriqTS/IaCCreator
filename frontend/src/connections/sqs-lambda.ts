import type { ConnectionSchema } from './registry';

export const sqsLambdaSchema: ConnectionSchema = {
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
