'use client';

import { useDiagramStore } from '@/store/diagram-store';
import { AWS_ICON_REGISTRY } from '@/data/aws-icon-registry';
import type { ServiceType } from '@/types/diagram';
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
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          backgroundColor: '#1e1e1e',
          borderTop: '1px solid rgba(255, 255, 255, 0.1)',
          padding: '16px 24px',
          zIndex: 50,
          color: 'rgba(255, 255, 255, 0.9)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {/* Source → Target label */}
          <span style={{ fontSize: '14px', fontWeight: 600 }}>
            {sourceEl?.name ?? 'Unknown'} → {targetEl?.name ?? 'Unknown'}
          </span>

          {/* Connection type dropdown */}
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
            <span style={{ color: 'rgba(255, 255, 255, 0.6)' }}>Type:</span>
            <select
              data-testid="connection-type-select"
              value={connector.connectionType}
              onChange={(e) => updateConnectorType(connector.id, e.target.value)}
              style={{
                backgroundColor: '#2a2a2a',
                color: '#fff',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                borderRadius: '4px',
                padding: '4px 8px',
                fontSize: '13px',
              }}
            >
              {CONNECTION_TYPE_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </label>

          {/* Spacer */}
          <div style={{ flex: 1 }} />

          {/* Delete button */}
          <button
            data-testid="delete-connector-btn"
            onClick={() => {
              removeConnector(selectedConnectorId);
              selectConnector(null);
            }}
            style={{
              backgroundColor: '#dc2626',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              padding: '6px 14px',
              fontSize: '13px',
              cursor: 'pointer',
            }}
          >
            Delete
          </button>
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
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        backgroundColor: '#1e1e1e',
        borderTop: '1px solid rgba(255, 255, 255, 0.1)',
        padding: '16px 24px',
        zIndex: 50,
        color: 'rgba(255, 255, 255, 0.9)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
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
        <input
          data-testid="element-name-input"
          type="text"
          value={element.name}
          onChange={(e) => updateElementName(element.id, e.target.value)}
          style={{
            backgroundColor: '#2a2a2a',
            color: '#fff',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            borderRadius: '4px',
            padding: '4px 8px',
            fontSize: '14px',
            fontWeight: 600,
            width: '200px',
          }}
        />

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Delete button */}
        <button
          data-testid="delete-element-btn"
          onClick={() => {
            removeElement(selectedElementId!);
            selectElement(null);
          }}
          style={{
            backgroundColor: '#dc2626',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            padding: '6px 14px',
            fontSize: '13px',
            cursor: 'pointer',
          }}
        >
          Delete
        </button>
      </div>

      {/* Service-specific config form */}
      <div data-testid="config-form-slot" style={{ marginTop: '12px' }}>
        <SchemaConfigForm elementId={element.id} serviceType={element.serviceType} />
      </div>
    </div>
  );
}
