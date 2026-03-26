'use client';

import { useDiagramStore } from '@/store/diagram-store';

export default function CloudWatchConfigForm({ elementId }: { elementId: string }) {
  const element = useDiagramStore((s) => s.elements.get(elementId));
  const updateElementConfig = useDiagramStore((s) => s.updateElementConfig);

  if (!element) return null;
  const config = element.config;

  return (
    <div data-testid="cloudwatch-config-form" style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'flex-end' }}>
      <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
        <span style={{ color: 'rgba(255,255,255,0.6)' }}>Retention (days)</span>
        <input
          data-testid="cloudwatch-retention-in-days"
          type="number"
          value={config.retention_in_days ?? ''}
          onChange={(e) => {
            const val = e.target.value === '' ? undefined : Number(e.target.value);
            if (val !== undefined && val < 0) return; // reject negative
            updateElementConfig(elementId, { retention_in_days: val });
          }}
          min={0}
          placeholder="30"
          style={inputStyle}
        />
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
