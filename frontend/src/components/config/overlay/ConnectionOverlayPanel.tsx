'use client';

import type { ArchitectureBlock, Connector } from '@/types/diagram';
import type { ConnectionSchema } from '@/connections';
import ConnectionConfigPanel from '@/connections/ConnectionConfigPanel';
import ConnectionContributionPreview from './ConnectionContributionPreview';
import { Label } from '@/components/ui/label';

interface ConnectionOverlayPanelProps {
  connector: Connector;
  sourceBlock: ArchitectureBlock;
  targetBlock: ArchitectureBlock;
  schema: ConnectionSchema;
}

/** Connection configuration, followed by what the backend says it will generate. */
export default function ConnectionOverlayPanel({
  connector,
  sourceBlock,
  targetBlock,
  schema,
}: ConnectionOverlayPanelProps) {
  return (
    <div data-testid="connection-overlay-panel" className="flex flex-col gap-6">
      {schema.fields.length > 0 && (
        <ConnectionConfigPanel
          connector={connector}
          sourceBlock={sourceBlock}
          targetBlock={targetBlock}
          schema={schema}
        />
      )}

      <div className="flex flex-col gap-2">
        <Label className="text-sm font-semibold text-foreground">What this generates</Label>
        <ConnectionContributionPreview connectorId={connector.id} />
      </div>
    </div>
  );
}
