'use client';

import { useDiagramStore } from '@/store/diagram-store';

const BILLING_MODE_OPTIONS = ['PAY_PER_REQUEST', 'PROVISIONED'];
const KEY_TYPE_OPTIONS = ['S', 'N', 'B'];

export default function DynamoDBConfigForm({ elementId }: { elementId: string }) {
  const element = useDiagramStore((s) => s.elements.get(elementId));
  const updateElementConfig = useDiagramStore((s) => s.updateElementConfig);

  if (!element) return null;
  const config = element.config;

  const hashKeyEmpty = (config.hash_key ?? '').trim() === '';

  return (
    <div data-testid="dynamodb-config-form" style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'flex-end' }}>
      {/* Billing Mode */}
      <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
        <span style={{ color: 'rgba(255,255,255,0.6)' }}>Billing Mode</span>
        <select
          data-testid="dynamodb-billing-mode"
          value={config.billing_mode ?? ''}
          onChange={(e) => updateElementConfig(elementId, { billing_mode: e.target.value })}
          style={inputStyle}
        >
          <option value="">Select</option>
          {BILLING_MODE_OPTIONS.map((o) => (
            <option key={o} value={o}>{o}</option>
          ))}
        </select>
      </label>

      {/* Hash Key */}
      <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
        <span style={{ color: 'rgba(255,255,255,0.6)' }}>Hash Key *</span>
        <input
          data-testid="dynamodb-hash-key"
          type="text"
          value={config.hash_key ?? ''}
          onChange={(e) => updateElementConfig(elementId, { hash_key: e.target.value })}
          placeholder="id"
          style={{
            ...inputStyle,
            borderColor: hashKeyEmpty ? '#dc2626' : 'rgba(255,255,255,0.2)',
          }}
        />
        {hashKeyEmpty && (
          <span data-testid="dynamodb-hash-key-error" style={{ color: '#f87171', fontSize: '11px' }}>
            Required
          </span>
        )}
      </label>

      {/* Hash Key Type */}
      <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
        <span style={{ color: 'rgba(255,255,255,0.6)' }}>Hash Key Type</span>
        <select
          data-testid="dynamodb-hash-key-type"
          value={config.hash_key_type ?? ''}
          onChange={(e) => updateElementConfig(elementId, { hash_key_type: e.target.value })}
          style={inputStyle}
        >
          <option value="">Select</option>
          {KEY_TYPE_OPTIONS.map((o) => (
            <option key={o} value={o}>{o}</option>
          ))}
        </select>
      </label>

      {/* Range Key */}
      <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
        <span style={{ color: 'rgba(255,255,255,0.6)' }}>Range Key</span>
        <input
          data-testid="dynamodb-range-key"
          type="text"
          value={config.range_key ?? ''}
          onChange={(e) => updateElementConfig(elementId, { range_key: e.target.value })}
          placeholder="(optional)"
          style={inputStyle}
        />
      </label>

      {/* Range Key Type */}
      <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
        <span style={{ color: 'rgba(255,255,255,0.6)' }}>Range Key Type</span>
        <select
          data-testid="dynamodb-range-key-type"
          value={config.range_key_type ?? ''}
          onChange={(e) => updateElementConfig(elementId, { range_key_type: e.target.value })}
          style={inputStyle}
        >
          <option value="">Select</option>
          {KEY_TYPE_OPTIONS.map((o) => (
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
