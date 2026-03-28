'use client';

import { useState } from 'react';
import type { TextObject } from '@/types/diagram';
import { MIN_OBJECT_WIDTH, MIN_OBJECT_HEIGHT } from '@/types/diagram';
import { useDiagramStore } from '@/store/diagram-store';

interface TextVisualConfigPanelProps {
  object: TextObject;
}

/** Visual configuration controls for text objects: font size, color, alignment, bold, italic, width, height. */
export default function TextVisualConfigPanel({ object }: TextVisualConfigPanelProps) {
  const updateVisualConfig = useDiagramStore((s) => s.updateVisualConfig);

  const [localWidth, setLocalWidth] = useState<string>(String(object.visualConfig.width));
  const [localHeight, setLocalHeight] = useState<string>(String(object.visualConfig.height));
  const [localFontSize, setLocalFontSize] = useState<string>(String(object.visualConfig.fontSize));

  const handleWidthChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLocalWidth(e.target.value);
    const val = Number(e.target.value);
    if (!Number.isNaN(val) && val >= MIN_OBJECT_WIDTH) {
      updateVisualConfig(object.id, { width: val });
    }
  };

  const handleWidthBlur = () => {
    const val = Number(localWidth);
    const clamped = Number.isNaN(val) ? MIN_OBJECT_WIDTH : Math.max(val, MIN_OBJECT_WIDTH);
    setLocalWidth(String(clamped));
    updateVisualConfig(object.id, { width: clamped });
  };

  const handleHeightChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLocalHeight(e.target.value);
    const val = Number(e.target.value);
    if (!Number.isNaN(val) && val >= MIN_OBJECT_HEIGHT) {
      updateVisualConfig(object.id, { height: val });
    }
  };

  const handleHeightBlur = () => {
    const val = Number(localHeight);
    const clamped = Number.isNaN(val) ? MIN_OBJECT_HEIGHT : Math.max(val, MIN_OBJECT_HEIGHT);
    setLocalHeight(String(clamped));
    updateVisualConfig(object.id, { height: clamped });
  };

  const handleFontSizeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLocalFontSize(e.target.value);
    const val = Number(e.target.value);
    if (!Number.isNaN(val) && val >= 8) {
      updateVisualConfig(object.id, { fontSize: val });
    }
  };

  const handleFontSizeBlur = () => {
    const val = Number(localFontSize);
    const clamped = Number.isNaN(val) ? 14 : Math.max(val, 8);
    setLocalFontSize(String(clamped));
    updateVisualConfig(object.id, { fontSize: clamped });
  };

  const handleFontColorChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    updateVisualConfig(object.id, { fontColor: e.target.value });
  };

  const handleTextAlignChange = (align: 'left' | 'center' | 'right') => {
    updateVisualConfig(object.id, { textAlign: align });
  };

  const handleBoldToggle = () => {
    updateVisualConfig(object.id, { bold: !object.visualConfig.bold });
  };

  const handleItalicToggle = () => {
    updateVisualConfig(object.id, { italic: !object.visualConfig.italic });
  };

  return (
    <div data-testid="text-visual-config" style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'flex-end' }}>
      <label style={labelStyle}>
        <span style={labelTextStyle}>Width (px)</span>
        <input
          data-testid="text-width"
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
          data-testid="text-height"
          type="number"
          value={localHeight}
          onChange={handleHeightChange}
          onBlur={handleHeightBlur}
          min={MIN_OBJECT_HEIGHT}
          style={inputStyle}
        />
      </label>

      <label style={labelStyle}>
        <span style={labelTextStyle}>Font Size</span>
        <input
          data-testid="text-font-size"
          type="number"
          value={localFontSize}
          onChange={handleFontSizeChange}
          onBlur={handleFontSizeBlur}
          min={8}
          style={inputStyle}
        />
      </label>

      <label style={labelStyle}>
        <span style={labelTextStyle}>Font Color</span>
        <input
          data-testid="text-font-color"
          type="color"
          value={object.visualConfig.fontColor}
          onChange={handleFontColorChange}
          style={{ ...inputStyle, width: '48px', padding: '2px', cursor: 'pointer' }}
        />
      </label>

      <div style={labelStyle}>
        <span style={labelTextStyle}>Alignment</span>
        <div style={{ display: 'flex', gap: '4px' }}>
          {(['left', 'center', 'right'] as const).map((align) => (
            <button
              key={align}
              data-testid={`text-align-${align}`}
              onClick={() => handleTextAlignChange(align)}
              style={{
                ...buttonStyle,
                background: object.visualConfig.textAlign === align ? 'rgba(59, 130, 246, 0.3)' : '#2a2a2a',
              }}
            >
              {align === 'left' ? '⫷' : align === 'center' ? '☰' : '⫸'}
            </button>
          ))}
        </div>
      </div>

      <div style={labelStyle}>
        <span style={labelTextStyle}>Style</span>
        <div style={{ display: 'flex', gap: '4px' }}>
          <button
            data-testid="text-bold"
            onClick={handleBoldToggle}
            style={{
              ...buttonStyle,
              fontWeight: 'bold',
              background: object.visualConfig.bold ? 'rgba(59, 130, 246, 0.3)' : '#2a2a2a',
            }}
          >
            B
          </button>
          <button
            data-testid="text-italic"
            onClick={handleItalicToggle}
            style={{
              ...buttonStyle,
              fontStyle: 'italic',
              background: object.visualConfig.italic ? 'rgba(59, 130, 246, 0.3)' : '#2a2a2a',
            }}
          >
            I
          </button>
        </div>
      </div>
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

const buttonStyle: React.CSSProperties = {
  width: '32px',
  height: '32px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  border: '1px solid rgba(255,255,255,0.2)',
  borderRadius: '4px',
  color: '#fff',
  fontSize: '13px',
  cursor: 'pointer',
};
