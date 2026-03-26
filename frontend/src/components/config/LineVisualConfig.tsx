'use client';

import type { LineObject, StrokeStyle } from '@/types/diagram';
import { useDiagramStore } from '@/store/diagram-store';

interface LineVisualConfigProps {
  object: LineObject;
}

/** Visual configuration controls for line objects: color, border width, stroke style, arrow toggles. */
export default function LineVisualConfig({ object }: LineVisualConfigProps) {
  const updateVisualConfig = useDiagramStore((s) => s.updateVisualConfig);

  const handleColorChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    updateVisualConfig(object.id, { color: e.target.value });
  };

  const handleBorderWidthChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number(e.target.value);
    if (!Number.isNaN(val) && val >= 1) {
      updateVisualConfig(object.id, { borderWidth: val });
    }
  };

  const handleStrokeStyleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    updateVisualConfig(object.id, { strokeStyle: e.target.value as StrokeStyle });
  };

  const handleStartArrowChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    updateVisualConfig(object.id, { startArrow: e.target.checked });
  };

  const handleEndArrowChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    updateVisualConfig(object.id, { endArrow: e.target.checked });
  };

  return (
    <div data-testid="line-visual-config" style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'flex-end' }}>
      <label style={labelStyle}>
        <span style={labelTextStyle}>Color</span>
        <input
          data-testid="line-color"
          type="color"
          value={object.visualConfig.color}
          onChange={handleColorChange}
          style={{ ...inputStyle, width: '48px', padding: '2px', cursor: 'pointer' }}
        />
      </label>

      <label style={labelStyle}>
        <span style={labelTextStyle}>Border Width</span>
        <input
          data-testid="line-border-width"
          type="number"
          value={object.visualConfig.borderWidth}
          onChange={handleBorderWidthChange}
          min={1}
          style={inputStyle}
        />
      </label>

      <label style={labelStyle}>
        <span style={labelTextStyle}>Stroke Style</span>
        <select
          data-testid="line-stroke-style"
          value={object.visualConfig.strokeStyle}
          onChange={handleStrokeStyleChange}
          style={inputStyle}
        >
          <option value="solid">Solid</option>
          <option value="dashed">Dashed</option>
        </select>
      </label>

      <label style={{ ...labelStyle, flexDirection: 'row', alignItems: 'center', gap: '6px' }}>
        <input
          data-testid="line-start-arrow"
          type="checkbox"
          checked={object.visualConfig.startArrow}
          onChange={handleStartArrowChange}
          style={{ accentColor: '#3b82f6', cursor: 'pointer' }}
        />
        <span style={labelTextStyle}>Start Arrow</span>
      </label>

      <label style={{ ...labelStyle, flexDirection: 'row', alignItems: 'center', gap: '6px' }}>
        <input
          data-testid="line-end-arrow"
          type="checkbox"
          checked={object.visualConfig.endArrow}
          onChange={handleEndArrowChange}
          style={{ accentColor: '#3b82f6', cursor: 'pointer' }}
        />
        <span style={labelTextStyle}>End Arrow</span>
      </label>
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '4px',
  fontSize: '13px',
};

const labelTextStyle: React.CSSProperties = {
  color: 'rgba(255,255,255,0.6)',
};

const inputStyle: React.CSSProperties = {
  backgroundColor: '#2a2a2a',
  color: '#fff',
  border: '1px solid rgba(255,255,255,0.2)',
  borderRadius: '4px',
  padding: '4px 8px',
  fontSize: '13px',
  width: '140px',
};
