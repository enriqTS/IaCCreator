'use client';

import type { ArchitectureBlock, Connector } from '@/types/diagram';
import { useConnectionPreview } from '@/store/connection-preview-store';
import type { ConnectionSchema } from '@/connections';
import ConnectionConfigPanel from '@/connections/ConnectionConfigPanel';
import ConnectionContributionPreview from './ConnectionContributionPreview';
import ConfigTabs, { type ConfigTab } from './ConfigTabs';

interface ConnectionOverlayPanelProps {
  connector: Connector;
  sourceBlock: ArchitectureBlock;
  targetBlock: ArchitectureBlock;
  schema: ConnectionSchema;
  /** Appended after the connection's own tabs, so the strip stays flat. */
  extraTabs?: ConfigTab[];
}

/** Connection configuration and what the backend says it will generate, as tabs. */
export default function ConnectionOverlayPanel({
  connector,
  sourceBlock,
  targetBlock,
  schema,
  extraTabs = [],
}: ConnectionOverlayPanelProps) {
  const preview = useConnectionPreview(connector.id);
  const tabs: ConfigTab[] = [];
  // A connection with no fields opens straight onto what it generates
  if (schema.fields.length > 0) {
    tabs.push({
      id: 'Settings',
      label: 'Settings',
      content: (
        <ConnectionConfigPanel
          connector={connector}
          sourceBlock={sourceBlock}
          targetBlock={targetBlock}
          schema={schema}
        />
      ),
    });
  }
  tabs.push({
    id: 'Generated',
    label: 'Generated',
    // What the backend says is wrong with the connection lives here, so flag it on the tab
    status: preview && preview.issues.length > 0 ? 'warning' : undefined,
    content: <ConnectionContributionPreview connectorId={connector.id} />,
  });
  tabs.push(...extraTabs);

  return (
    <div data-testid="connection-overlay-panel" className="min-w-0">
      <ConfigTabs testIdPrefix="connection" tabs={tabs} />
    </div>
  );
}
