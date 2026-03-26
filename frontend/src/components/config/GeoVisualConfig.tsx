'use client';

import { useState } from 'react';
import type { GeometricObject, GeometricShape } from '@/types/diagram';
import { MIN_OBJECT_WIDTH, MIN_OBJECT_HEIGHT } from '@/types/diagram';
import { useDiagramStore } from '@/store/diagram-store';

interface GeoVisualConfigProps {
  object: GeometricObject;
}

/** Visual configuration controls for geometric objects: width, height, fill, colors, border, shape. */
export default function GeoVisualConfig({ object }: GeoVisualConfigProps) {
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

  const handleFillToggle = (e: React.ChangeEvent<HTMLInputElement>) => {
    updateVisualConfig(object.id, { fill: e.target.checked });
  };

  const handleFillColorChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    updateVisualConfig(object.id, { fillColor: e.target.value });
  };

  const handleBorderColorChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    updateVisualConfig(object.id, { borderColor: e.target.value });
  };

  const handleBorderWidthChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number(e.target.value);
    if (!Number.isNaN(val) && val >= 1) {
      updateVisualConfig(object.id, { borderWidth: val });
    }
  };

  const handleShapeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    updateVisualConfig(object.id, { shape: e.target.value as GeometricShape });
  };

  return (
    <div data-testid="geo-visual-config" style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'flex-end' }}>
      <label style={labelStyle}>
        <span style={labelTextStyle}>Width (px)</span>
        <input
          data-testid="geo-width"
          type="number"
          value={localWidth}
          onChange={handleWidthChange}
          onBlur={handleWidthBlur}
          min={MIN_OBJECT_WIDTH}
          style={inputStyle}
        />
      </label>

      <label style={labelStyle}>
        <span style={labelTextStyle}>Height (px)</span>
        <input
          data-testid="geo-height"
          type="number"
          value={localHeight}
          onChange={handleHeightChange}
          onBlur={handleHeightBlur}
          min={MIN_OBJECT_HEIGHT}
          style={inputStyle}
        />
      </label>

      <label style={{ ...labelStyle, flexDirection: 'row', alignItems: 'center', gap: '6px' }}>
        <input
          data-testid="geo-fill-toggle"
          type="checkbox"
          checked={object.visualConfig.fill}
          onChange={handleFillToggle}
          style={{ accentColor: '#3b82f6', cursor: 'pointer' }}
        />
        <span style={labelTextStyle}>Fill</span>
      </label>

      <label style={labelStyle}>
        <span style={labelTextStyle}>Fill Color</span>
        <input
          data-testid="geo-fill-color"
          type="color"
          value={object.visualConfig.fillColor}
          onChange={handleFillColorChange}
          disabled={!object.visualConfig.fill}
          style={{ ...inputStyle, width: '48px', padding: '2px', cursor: object.visualConfig.fill ? 'pointer' : 'not-allowed', opacity: object.visualConfig.fill ? 1 : 0.4 }}
        />
      </label>

      <label style={labelStyle}>
        <span style={labelTextStyle}>Border Color</span>
        <input
          data-testid="geo-border-color"
          type="color"
          value={object.visualConfig.borderColor}
          onChange={handleBorderColorChange}
          style={{ ...inputStyle, width: '48px', padding: '2px', cursor: 'pointer' }}
        />
      </label>

      <label style={labelStyle}>
        <span style={labelTextStyle}>Border Width</span>
        <input
          data-testid="geo-border-width"
          type="number"
          value={object.visualConfig.borderWidth}
          onChange={handleBorderWidthChange}
          min={1}
          style={inputStyle}
        />
      </label>

      <label style={labelStyle}>
        <span style={labelTextStyle}>Shape</span>
        <select
          data-testid="geo-shape"
          value={object.visualConfig.shape}
          onChange={handleShapeChange}
          style={inputStyle}
        >
          <option value="rectangle">Rectangle</option>
          <option value="ellipse">Ellipse</option>
        </select>
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
