import type { ConnectionSchema } from './registry';

export const lambdaSqsSchema: ConnectionSchema = {
  sourcePair: ['lambda', 'sqs'],
  label: 'Lambda → SQS',
  fields: [],
  getLabel: () => 'Send Message',
};
