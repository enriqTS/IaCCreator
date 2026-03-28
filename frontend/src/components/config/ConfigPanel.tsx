'use client';

import { useDiagramStore } from '@/store/diagram-store';
import { AWS_ICON_REGISTRY } from '@/data/aws-icon-registry';
import type { ServiceType } from '@/types/diagram';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import SchemaConfigForm from './SchemaConfigForm';

/** Look up the icon path for a given service type from the registry. */
function getIconPath(serviceType: ServiceType): string {
  for (const category of AWS_ICON_REGISTRY) {
    for (const service of category.services) {
      if (service.serviceType === serviceType) return service.iconPath;
    }
  }
  return '';
}

const CONNECTION_TYPE_OPTIONS = ['triggers', 'reads_from', 'writes_to', 'invokes'];

export default function ConfigPanel() {
  const selectedElementId = useDiagramStore((s) => s.selectedElementId);
  const selectedConnectorId = useDiagramStore((s) => s.selectedConnectorId);
  const elements = useDiagramStore((s) => s.elements);
  const connectors = useDiagramStore((s) => s.connectors);
  const updateElementName = useDiagramStore((s) => s.updateElementName);
  const removeElement = useDiagramStore((s) => s.removeElement);
  const selectElement = useDiagramStore((s) => s.selectElement);
  const updateConnectorType = useDiagramStore((s) => s.updateConnectorType);
  const removeConnector = useDiagramStore((s) => s.removeConnector);
  const selectConnector = useDiagramStore((s) => s.selectConnector);

  // Nothing selected — render nothing
  if (!selectedElementId && !selectedConnectorId) return null;

  // --- Connector selected ---
  if (selectedConnectorId) {
    const connector = connectors.get(selectedConnectorId);
    if (!connector) return null;

    const sourceEl = elements.get(connector.sourceId);
    const targetEl = elements.get(connector.targetId);

    return (
      <div
        data-testid="config-panel"
        className="fixed bottom-0 left-0 right-0 bg-[#1e1e1e] border-t border-white/10 px-6 py-4 z-50 text-white/90"
      >
        <div className="flex items-center gap-4">
          {/* Source → Target label */}
          <span className="text-sm font-semibold">
            {sourceEl?.name ?? 'Unknown'} → {targetEl?.name ?? 'Unknown'}
          </span>

          {/* Connection type dropdown */}
          <div className="flex items-center gap-2 text-[13px]">
            <Label className="text-muted-foreground">Type:</Label>
            <Select
              value={connector.connectionType}
              onValueChange={(value) => updateConnectorType(connector.id, value)}
            >
              <SelectTrigger data-testid="connection-type-select" className="w-auto">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CONNECTION_TYPE_OPTIONS.map((opt) => (
                  <SelectItem key={opt} value={opt}>
                    {opt}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Delete button */}
          <Button
            data-testid="delete-connector-btn"
            variant="destructive"
            size="sm"
            onClick={() => {
              removeConnector(selectedConnectorId);
              selectConnector(null);
            }}
          >
            Delete
          </Button>
        </div>
      </div>
    );
  }

  // --- Element selected ---
  const element = elements.get(selectedElementId!);
  if (!element) return null;

  const iconPath = getIconPath(element.serviceType);

  return (
    <div
      data-testid="config-panel"
      className="fixed bottom-0 left-0 right-0 bg-[#1e1e1e] border-t border-white/10 px-6 py-4 z-50 text-white/90"
    >
      <div className="flex items-center gap-4">
        {/* Service icon */}
        {iconPath && (
          <img
            src={iconPath}
            alt={element.serviceType}
            width={32}
            height={32}
            draggable={false}
          />
        )}

        {/* Editable name input */}
        <Input
          data-testid="element-name-input"
          type="text"
          value={element.name}
          onChange={(e) => updateElementName(element.id, e.target.value)}
          className="w-[200px] text-sm font-semibold"
        />

        {/* Spacer */}
        <div className="flex-1" />

        {/* Delete button */}
        <Button
          data-testid="delete-element-btn"
          variant="destructive"
          size="sm"
          onClick={() => {
            removeElement(selectedElementId!);
            selectElement(null);
          }}
        >
          Delete
        </Button>
      </div>

      {/* Service-specific config form */}
      <div data-testid="config-form-slot" className="mt-3">
        <SchemaConfigForm elementId={element.id} serviceType={element.serviceType} />
      </div>
    </div>
  );
}
