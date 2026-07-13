import type { ConnectionSchema } from './registry';

export const lambdaSnsSchema: ConnectionSchema = {
  sourcePair: ['lambda', 'sns'],
  label: 'Lambda → SNS',
  fields: [],
  getLabel: () => 'Publish',
};
