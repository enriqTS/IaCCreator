'use client';

import { useDiagramStore } from '@/store/diagram-store';

const RUNTIME_OPTIONS = ['nodejs18.x', 'nodejs20.x', 'python3.12', 'python3.11'];

export default function LambdaConfigForm({ elementId }: { elementId: string }) {
  const element = useDiagramStore((s) => s.elements.get(elementId));
  const updateElementConfig = useDiagramStore((s) => s.updateElementConfig);

  if (!element) return null;
  const config = element.config;

  return (
    <div data-testid="lambda-config-form" style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'flex-end' }}>
      {/* Handler */}
      <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
        <span style={{ color: 'rgba(255,255,255,0.6)' }}>Handler</span>
        <input
          data-testid="lambda-handler"
          type="text"
          value={config.handler ?? ''}
          onChange={(e) => updateElementConfig(elementId, { handler: e.target.value })}
          placeholder="index.handler"
          style={inputStyle}
        />
      </label>

      {/* Runtime */}
      <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
        <span style={{ color: 'rgba(255,255,255,0.6)' }}>Runtime</span>
        <select
          data-testid="lambda-runtime"
          value={config.runtime ?? ''}
          onChange={(e) => updateElementConfig(elementId, { runtime: e.target.value })}
          style={inputStyle}
        >
          <option value="">Select runtime</option>
          {RUNTIME_OPTIONS.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
      </label>

      {/* Memory Size */}
      <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
        <span style={{ color: 'rgba(255,255,255,0.6)' }}>Memory (MB)</span>
        <input
          data-testid="lambda-memory-size"
          type="number"
          value={config.memory_size ?? ''}
          onChange={(e) => {
            const val = e.target.value === '' ? undefined : Number(e.target.value);
            if (val !== undefined && val < 0) return; // reject negative
            updateElementConfig(elementId, { memory_size: val });
          }}
          min={0}
          placeholder="128"
          style={inputStyle}
        />
      </label>

      {/* Timeout */}
      <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
        <span style={{ color: 'rgba(255,255,255,0.6)' }}>Timeout (s)</span>
        <input
          data-testid="lambda-timeout"
          type="number"
          value={config.timeout ?? ''}
          onChange={(e) => {
            const val = e.target.value === '' ? undefined : Number(e.target.value);
            if (val !== undefined && val < 0) return; // reject negative
            updateElementConfig(elementId, { timeout: val });
          }}
          min={0}
          placeholder="3"
          style={inputStyle}
        />
      </label>

      {/* Is Layer */}
      <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', paddingBottom: '2px' }}>
        <input
          data-testid="lambda-is-layer"
          type="checkbox"
          checked={config.is_layer ?? false}
          onChange={(e) => updateElementConfig(elementId, { is_layer: e.target.checked })}
        />
        <span style={{ color: 'rgba(255,255,255,0.6)' }}>Is Layer</span>
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
