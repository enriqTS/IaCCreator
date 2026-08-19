/**
 * Presentation for connections — how a wired line reads on the canvas.
 *
 * Field definitions come from the backend catalog; only the visual treatment
 * of a connection lives here.
 */

import type { ServiceType } from '@/types/diagram';

export type ConnectionConfigValues = Record<string, string | number | boolean>;

export interface ConnectionPresentation {
  getLabel: (config: ConnectionConfigValues) => string | null;
  getDashed?: (config: ConnectionConfigValues) => boolean;
}

/** Key is "source::target::connectionType". */
export type PresentationKey = `${ServiceType}::${ServiceType}::${string}`;

function accessPatternLabel(config: ConnectionConfigValues): string {
  const pattern = config.access_pattern as string;
  if (pattern === 'read') return 'Read Only';
  if (pattern === 'write') return 'Write Only';
  return 'Read/Write';
}

export const CONNECTION_PRESENTATION = new Map<PresentationKey, ConnectionPresentation>([
  [
    'api-gateway::lambda::route_handler',
    {
      // Routes are listed in the panel instead, since several may target one function
      getLabel: () => null,
    },
  ],
  [
    'api-gateway::lambda::authorizer',
    {
      getLabel: (config) => `Authorizer: ${config.authorizer_name || 'auth'}`,
      getDashed: () => true,
    },
  ],
  ['lambda::dynamodb::accesses', { getLabel: accessPatternLabel }],
  ['lambda::s3::accesses', { getLabel: accessPatternLabel }],
  ['lambda::cloudwatch::logs_to', { getLabel: () => 'Logs' }],
  ['lambda::sns::publishes_to', { getLabel: () => 'Publish' }],
  ['lambda::sqs::sends_to', { getLabel: () => 'Send' }],
  ['sqs::lambda::triggers', { getLabel: (config) => `Event Source (batch: ${config.batch_size ?? 10})` }],
  ['sns::sqs::delivers_to', { getLabel: () => 'Deliver' }],
  ['sns::lambda::triggers', { getLabel: () => 'Trigger' }],
]);

export function getPresentation(
  source: ServiceType,
  target: ServiceType,
  connectionType: string,
): ConnectionPresentation | null {
  return (
    CONNECTION_PRESENTATION.get(`${source}::${target}::${connectionType}`) ?? null
  );
}
