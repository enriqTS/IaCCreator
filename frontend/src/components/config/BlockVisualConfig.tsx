'use client';

import { useState } from 'react';
import type { ArchitectureBlock } from '@/types/diagram';
import { MIN_OBJECT_WIDTH, MIN_OBJECT_HEIGHT } from '@/types/diagram';
import { useDiagramStore } from '@/store/diagram-store';

interface BlockVisualConfigProps {
  object: ArchitectureBlock;
}

/** Width and height configuration for architecture blocks. */
export default function BlockVisualConfig({ object }: BlockVisualConfigProps) {
  const updateVisualConfig = useDiagramStore((s) => s.updateVisualConfig);

  const [localWidth, setLocalWidth] = useState<string>(String(object.visualConfig.width));
  const [localHeight, setLocalHeight] = useState<string>(String(object.visualConfig.height));

  const handleWidthChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLocalWidth(e.target.value);
    const val = Number(e.target.value);
    if (!Number.isNaN(val) && val >= MIN_OBJECT_WIDTH) {
      updateVisualConfig(object.id, { width: val });
    }
  };

  const handleHeightChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLocalHeight(e.target.value);
    const val = Number(e.target.value);
    if (!Number.isNaN(val) && val >= MIN_OBJECT_HEIGHT) {
      updateVisualConfig(object.id, { height: val });
    }
  };

  const handleWidthBlur = () => {
    const val = Number(localWidth);
    const clamped = Number.isNaN(val) ? MIN_OBJECT_WIDTH : Math.max(val, MIN_OBJECT_WIDTH);
    setLocalWidth(String(clamped));
    updateVisualConfig(object.id, { width: clamped });
  };

  const handleHeightBlur = () => {
    const val = Number(localHeight);
    const clamped = Number.isNaN(val) ? MIN_OBJECT_HEIGHT : Math.max(val, MIN_OBJECT_HEIGHT);
    setLocalHeight(String(clamped));
    updateVisualConfig(object.id, { height: clamped });
  };

  return (
    <div data-testid="block-visual-config" style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'flex-end' }}>
      <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
        <span style={{ color: 'rgba(255,255,255,0.6)' }}>Width (px)</span>
        <input
          data-testid="block-width"
          type="number"
          value={localWidth}
          onChange={handleWidthChange}
          onBlur={handleWidthBlur}
          min={MIN_OBJECT_WIDTH}
          style={inputStyle}
        />
      </label>

      <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
        <span style={{ color: 'rgba(255,255,255,0.6)' }}>Height (px)</span>
        <input
          data-testid="block-height"
          type="number"
          value={localHeight}
          onChange={handleHeightChange}
          onBlur={handleHeightBlur}
          min={MIN_OBJECT_HEIGHT}
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
