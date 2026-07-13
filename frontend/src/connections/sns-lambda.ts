import type { ConnectionSchema } from './registry';

export const snsLambdaSchema: ConnectionSchema = {
  sourcePair: ['sns', 'lambda'],
  label: 'SNS → Lambda',
  fields: [],
  getLabel: () => 'Subscription',
};
