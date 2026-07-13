import type { ConnectionSchema } from './registry';

export const snsSqsSchema: ConnectionSchema = {
  sourcePair: ['sns', 'sqs'],
  label: 'SNS → SQS',
  fields: [],
  getLabel: () => 'Subscription',
};
