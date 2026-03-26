'use client';

import { useDiagramStore } from '@/store/diagram-store';

export default function S3ConfigForm({ elementId }: { elementId: string }) {
  const element = useDiagramStore((s) => s.elements.get(elementId));
  const updateElementConfig = useDiagramStore((s) => s.updateElementConfig);

  if (!element) return null;
  const config = element.config;

  return (
    <div data-testid="s3-config-form" style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'flex-end' }}>
      <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
        <input
          data-testid="s3-versioning"
          type="checkbox"
          checked={config.versioning ?? false}
          onChange={(e) => updateElementConfig(elementId, { versioning: e.target.checked })}
        />
        <span style={{ color: 'rgba(255,255,255,0.6)' }}>Versioning</span>
      </label>
    </div>
  );
}
