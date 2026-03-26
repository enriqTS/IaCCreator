'use client';

import { useDiagramStore } from '@/store/diagram-store';

const PROTOCOL_OPTIONS = ['HTTP', 'WEBSOCKET'];

export default function APIGatewayConfigForm({ elementId }: { elementId: string }) {
  const element = useDiagramStore((s) => s.elements.get(elementId));
  const updateElementConfig = useDiagramStore((s) => s.updateElementConfig);

  if (!element) return null;
  const config = element.config;

  return (
    <div data-testid="apigateway-config-form" style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'flex-end' }}>
      <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
        <span style={{ color: 'rgba(255,255,255,0.6)' }}>Protocol Type</span>
        <select
          data-testid="apigateway-protocol-type"
          value={config.protocol_type ?? ''}
          onChange={(e) => updateElementConfig(elementId, { protocol_type: e.target.value })}
          style={inputStyle}
        >
          <option value="">Select</option>
          {PROTOCOL_OPTIONS.map((o) => (
            <option key={o} value={o}>{o}</option>
          ))}
        </select>
      </label>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  backgroundColor: '#2a2a2a',
  color: '#fff',
  border: '1px solid rgba(255,255,255,0.2)',
  borderRadius: '4px',
  padding: '4px 8px',
  fontSize: '13px',
  width: '140px',
};
