'use client';

import type { ReactNode } from 'react';
import type {
  ArchitectureBlock,
  CanvasObject,
  CanvasObjectType,
  Connector,
  LineObject,
} from '@/types/diagram';
import { getSchemas } from '@/store/schema-store';
import { getServiceDisplayName } from '@/data/aws-icon-registry';
import { findConnectorForLine, getSchemaForConnector } from '@/connections/connector-utils';
import SchemaConfigForm from '../schema/SchemaConfigForm';
import ApigwDynamicConfigUI from '../apigw/ApigwDynamicConfigUI';
import ConnectionOverlayPanel from './ConnectionOverlayPanel';

/** What the overlay container needs in order to render one kind of thing. */
export interface ConfigOverlayPanel {
  /** Identity of the configured thing, so the container resets when it changes. */
  key: string;
  title: string;
  subtitle: string;
  content: ReactNode;
}

/** The diagram state a resolver may read; passing it in keeps resolvers pure. */
export interface OverlayContext {
  canvasObjects: Map<string, CanvasObject>;
  connectors: Map<string, Connector>;
}

type PanelResolver = (
  selected: CanvasObject,
  context: OverlayContext,
) => ConfigOverlayPanel | null;

function resolveArchitectureBlock(selected: CanvasObject): ConfigOverlayPanel | null {
  const block = selected as ArchitectureBlock;
  const subtitle = getServiceDisplayName(block.serviceType);

  // API Gateway carries its own editor rather than a flat schema form
  if (block.serviceType === 'api-gateway') {
    return {
      key: block.id,
      title: block.name,
      subtitle,
      content: <ApigwDynamicConfigUI elementId={block.id} />,
    };
  }

  // Never open an empty overlay: a service with no schema has nothing to configure
  const entries = getSchemas()[block.serviceType] ?? [];
  if (entries.length === 0) return null;

  return {
    key: block.id,
    title: block.name,
    subtitle,
    content: <SchemaConfigForm elementId={block.id} serviceType={block.serviceType} />,
  };
}

function resolveLine(
  selected: CanvasObject,
  context: OverlayContext,
): ConfigOverlayPanel | null {
  const line = selected as LineObject;
  const connector = findConnectorForLine(line, context.connectors, context.canvasObjects);
  if (!connector) return null;

  const schema = getSchemaForConnector(connector, context.canvasObjects);
  const sourceBlock = context.canvasObjects.get(connector.sourceId);
  const targetBlock = context.canvasObjects.get(connector.targetId);
  if (
    !schema ||
    sourceBlock?.objectType !== 'architecture-block' ||
    targetBlock?.objectType !== 'architecture-block'
  ) {
    return null;
  }

  return {
    key: connector.id,
    title: `${sourceBlock.name} → ${targetBlock.name}`,
    subtitle: schema.label,
    content: (
      <ConnectionOverlayPanel
        connector={connector}
        sourceBlock={sourceBlock}
        targetBlock={targetBlock}
        schema={schema}
      />
    ),
  };
}

const RESOLVERS: Partial<Record<CanvasObjectType, PanelResolver>> = {
  'architecture-block': resolveArchitectureBlock,
  line: resolveLine,
};

/** The panel for a selected object, or null when it has nothing to configure. */
export function resolveConfigOverlayPanel(
  selected: CanvasObject | null,
  context: OverlayContext,
): ConfigOverlayPanel | null {
  if (!selected) return null;
  return RESOLVERS[selected.objectType]?.(selected, context) ?? null;
}
