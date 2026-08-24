'use client';

import type { ReactNode } from 'react';
import type {
  ArchitectureBlock,
  CanvasObject,
  CanvasObjectType,
  Connector,
  LineObject,
} from '@/types/diagram';
import { getServiceDisplayName } from '@/data/aws-icon-registry';
import { findConnectorForLine, getSchemaForConnector } from '@/connections/connector-utils';
import SchemaConfigForm from '../schema/SchemaConfigForm';
import ApigwDynamicConfigUI from '../apigw/ApigwDynamicConfigUI';
import VisualTab from '../visual/VisualTab';
import ConfigTabs, { type ConfigTab } from './ConfigTabs';
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

/** Every object is configurable visually, so every panel ends with this tab. */
function visualTab(object: CanvasObject): ConfigTab {
  return {
    id: 'Visual',
    label: 'Visual',
    content: <VisualTab object={object} />,
  };
}

function resolveArchitectureBlock(selected: CanvasObject): ConfigOverlayPanel {
  const block = selected as ArchitectureBlock;
  const panel = {
    key: block.id,
    title: block.name,
    subtitle: getServiceDisplayName(block.serviceType),
  };

  // API Gateway carries its own editor rather than a flat schema form
  if (block.serviceType === 'api-gateway') {
    return {
      ...panel,
      content: <ApigwDynamicConfigUI elementId={block.id} extraTabs={[visualTab(block)]} />,
    };
  }

  return {
    ...panel,
    content: (
      <SchemaConfigForm
        elementId={block.id}
        serviceType={block.serviceType}
        extraTabs={[visualTab(block)]}
      />
    ),
  };
}

function resolveLine(
  selected: CanvasObject,
  context: OverlayContext,
): ConfigOverlayPanel {
  const line = selected as LineObject;
  const connector = findConnectorForLine(line, context.connectors, context.canvasObjects);
  const schema = connector ? getSchemaForConnector(connector, context.canvasObjects) : null;
  const sourceBlock = connector ? context.canvasObjects.get(connector.sourceId) : undefined;
  const targetBlock = connector ? context.canvasObjects.get(connector.targetId) : undefined;

  // A line that carries a generatable connection configures that connection too
  if (
    connector &&
    schema &&
    sourceBlock?.objectType === 'architecture-block' &&
    targetBlock?.objectType === 'architecture-block'
  ) {
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
          extraTabs={[visualTab(line)]}
        />
      ),
    };
  }

  return visualOnlyPanel(line, 'Line');
}

/** Objects with nothing but appearance to configure still open the same surface. */
function visualOnlyPanel(object: CanvasObject, subtitle: string): ConfigOverlayPanel {
  return {
    key: object.id,
    title: object.name,
    subtitle,
    content: <ConfigTabs testIdPrefix="visual" tabs={[visualTab(object)]} />,
  };
}

const RESOLVERS: Partial<Record<CanvasObjectType, PanelResolver>> = {
  'architecture-block': resolveArchitectureBlock,
  line: resolveLine,
  geometric: (selected) => visualOnlyPanel(selected, 'Shape'),
  text: (selected) => visualOnlyPanel(selected, 'Text'),
  uml: (selected) => visualOnlyPanel(selected, 'UML'),
};

/** The panel for a selected object, or null when its type has none. */
export function resolveConfigOverlayPanel(
  selected: CanvasObject | null,
  context: OverlayContext,
): ConfigOverlayPanel | null {
  if (!selected) return null;
  return RESOLVERS[selected.objectType]?.(selected, context) ?? null;
}
