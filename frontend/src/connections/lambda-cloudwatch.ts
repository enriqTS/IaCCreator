import type { ConnectionSchema } from './registry';

export const lambdaCloudwatchSchema: ConnectionSchema = {
  sourcePair: ['lambda', 'cloudwatch'],
  label: 'Lambda → CloudWatch',
  fields: [],
  getLabel: () => 'Logging',
};
