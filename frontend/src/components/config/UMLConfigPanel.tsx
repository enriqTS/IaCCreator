'use client';

import { useState } from 'react';
import type { UMLObject } from '@/types/diagram';
import { useDiagramStore } from '@/store/diagram-store';

interface UMLConfigPanelProps {
  object: UMLObject;
}

/** Configuration panel for UML objects: kind display, attributes/methods editor, visual config. */
export default function UMLConfigPanel({ object }: UMLConfigPanelProps) {
  const updateVisualConfig = useDiagramStore((s) => s.updateVisualConfig);
  const updateCanvasObject = useDiagramStore((s) => s.updateCanvasObject);

  const [newAttribute, setNewAttribute] = useState('');
  const [newMethod, setNewMethod] = useState('');

  const hasClassData = object.umlKind === 'class' || object.umlKind === 'interface';
  const attributes = object.classData?.attributes ?? [];
  const methods = object.classData?.methods ?? [];

  const handleAddAttribute = () => {
    if (!newAttribute.trim()) return;
    const updated = [...attributes, newAttribute.trim()];
    updateCanvasObject(object.id, {
      classData: { ...object.classData, attributes: updated, methods },
    } as Partial<UMLObject>);
    setNewAttribute('');
  };

  const handleRemoveAttribute = (index: number) => {
    const updated = attributes.filter((_, i) => i !== index);
    updateCanvasObject(object.id, {
      classData: { ...object.classData, attributes: updated, methods },
    } as Partial<UMLObject>);
  };

  const handleAddMethod = () => {
    if (!newMethod.trim()) return;
    const updated = [...methods, newMethod.trim()];
    updateCanvasObject(object.id, {
      classData: { ...object.classData, attributes, methods: updated },
    } as Partial<UMLObject>);
    setNewMethod('');
  };

  const handleRemoveMethod = (index: number) => {
    const updated = methods.filter((_, i) => i !== index);
    updateCanvasObject(object.id, {
      classData: { ...object.classData, attributes, methods: updated },
    } as Partial<UMLObject>);
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

  const handleHeaderColorChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    updateVisualConfig(object.id, { headerColor: e.target.value });
  };

  return (
    <div data-testid="uml-config-panel" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* UML Kind (read-only) */}
      <div style={labelStyle}>
        <span style={labelTextStyle}>UML Kind</span>
        <span data-testid="uml-kind" style={{ color: '#fff', fontSize: 13, textTransform: 'capitalize' }}>
          {object.umlKind}
        </span>
      </div>

      {/* Visual config controls */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'flex-end' }}>
        <label style={labelStyle}>
          <span style={labelTextStyle}>Fill Color</span>
          <input
            data-testid="uml-fill-color"
            type="color"
            value={object.visualConfig.fillColor}
            onChange={handleFillColorChange}
            style={{ ...inputStyle, width: '48px', padding: '2px', cursor: 'pointer' }}
          />
        </label>

        <label style={labelStyle}>
          <span style={labelTextStyle}>Border Color</span>
          <input
            data-testid="uml-border-color"
            type="color"
            value={object.visualConfig.borderColor}
            onChange={handleBorderColorChange}
            style={{ ...inputStyle, width: '48px', padding: '2px', cursor: 'pointer' }}
          />
        </label>

        <label style={labelStyle}>
          <span style={labelTextStyle}>Border Width</span>
          <input
            data-testid="uml-border-width"
            type="number"
            value={object.visualConfig.borderWidth}
            onChange={handleBorderWidthChange}
            min={1}
            style={inputStyle}
          />
        </label>

        <label style={labelStyle}>
          <span style={labelTextStyle}>Header Color</span>
          <input
            data-testid="uml-header-color"
            type="color"
            value={object.visualConfig.headerColor}
            onChange={handleHeaderColorChange}
            style={{ ...inputStyle, width: '48px', padding: '2px', cursor: 'pointer' }}
          />
        </label>
      </div>

      {/* Attributes and Methods (class/interface only) */}
      {hasClassData && (
        <>
          {/* Attributes */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <span style={{ ...labelTextStyle, fontWeight: 600 }}>Attributes</span>
            {attributes.map((attr, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span data-testid={`uml-attribute-${i}`} style={{ color: '#fff', fontSize: 13, flex: 1 }}>{attr}</span>
                <button
                  data-testid={`uml-remove-attribute-${i}`}
                  onClick={() => handleRemoveAttribute(i)}
                  style={removeButtonStyle}
                >
                  ✕
                </button>
              </div>
            ))}
            <div style={{ display: 'flex', gap: '6px' }}>
              <input
                data-testid="uml-new-attribute"
                type="text"
                placeholder="New attribute..."
                value={newAttribute}
                onChange={(e) => setNewAttribute(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleAddAttribute(); }}
                style={{ ...inputStyle, flex: 1 }}
              />
              <button
                data-testid="uml-add-attribute"
                onClick={handleAddAttribute}
                style={addButtonStyle}
              >
                +
              </button>
            </div>
          </div>

          {/* Methods */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <span style={{ ...labelTextStyle, fontWeight: 600 }}>Methods</span>
            {methods.map((method, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span data-testid={`uml-method-${i}`} style={{ color: '#fff', fontSize: 13, flex: 1 }}>{method}</span>
                <button
                  data-testid={`uml-remove-method-${i}`}
                  onClick={() => handleRemoveMethod(i)}
                  style={removeButtonStyle}
                >
                  ✕
                </button>
              </div>
            ))}
            <div style={{ display: 'flex', gap: '6px' }}>
              <input
                data-testid="uml-new-method"
                type="text"
                placeholder="New method..."
                value={newMethod}
                onChange={(e) => setNewMethod(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleAddMethod(); }}
                style={{ ...inputStyle, flex: 1 }}
              />
              <button
                data-testid="uml-add-method"
                onClick={handleAddMethod}
                style={addButtonStyle}
              >
                +
              </button>
            </div>
          </div>
        </>
      )}
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

const removeButtonStyle: React.CSSProperties = {
  width: '24px',
  height: '24px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  border: '1px solid rgba(255,255,255,0.2)',
  borderRadius: '4px',
  background: '#2a2a2a',
  color: '#ff6b6b',
  fontSize: '11px',
  cursor: 'pointer',
};

const addButtonStyle: React.CSSProperties = {
  width: '32px',
  height: '32px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  border: '1px solid rgba(255,255,255,0.2)',
  borderRadius: '4px',
  background: '#2a2a2a',
  color: '#4ade80',
  fontSize: '16px',
  cursor: 'pointer',
};
