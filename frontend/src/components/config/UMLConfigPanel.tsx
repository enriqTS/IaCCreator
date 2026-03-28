'use client';

import { useState } from 'react';
import type { UMLObject } from '@/types/diagram';
import { useDiagramStore } from '@/store/diagram-store';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';

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
    <div data-testid="uml-config-panel" className="flex flex-col gap-4">
      {/* UML Kind (read-only) */}
      <div className="flex flex-col gap-1 text-[13px]">
        <Label className="text-xs text-muted-foreground">UML Kind</Label>
        <span data-testid="uml-kind" className="text-foreground text-[13px] capitalize">
          {object.umlKind}
        </span>
      </div>

      {/* Visual config controls */}
      <div className="flex flex-wrap gap-3 items-end">
        <div className="flex flex-col gap-1 text-[13px]">
          <Label className="text-xs text-muted-foreground">Fill Color</Label>
          <input
            data-testid="uml-fill-color"
            type="color"
            value={object.visualConfig.fillColor}
            onChange={handleFillColorChange}
            className="w-12 h-9 p-0.5 cursor-pointer rounded-md border border-input bg-transparent"
          />
        </div>

        <div className="flex flex-col gap-1 text-[13px]">
          <Label className="text-xs text-muted-foreground">Border Color</Label>
          <input
            data-testid="uml-border-color"
            type="color"
            value={object.visualConfig.borderColor}
            onChange={handleBorderColorChange}
            className="w-12 h-9 p-0.5 cursor-pointer rounded-md border border-input bg-transparent"
          />
        </div>

        <div className="flex flex-col gap-1 text-[13px]">
          <Label className="text-xs text-muted-foreground">Border Width</Label>
          <Input
            data-testid="uml-border-width"
            type="text"
            inputMode="numeric"
            value={object.visualConfig.borderWidth}
            onChange={handleBorderWidthChange}
            className="w-[140px]"
          />
        </div>

        <div className="flex flex-col gap-1 text-[13px]">
          <Label className="text-xs text-muted-foreground">Header Color</Label>
          <input
            data-testid="uml-header-color"
            type="color"
            value={object.visualConfig.headerColor}
            onChange={handleHeaderColorChange}
            className="w-12 h-9 p-0.5 cursor-pointer rounded-md border border-input bg-transparent"
          />
        </div>
      </div>

      {/* Attributes and Methods (class/interface only) */}
      {hasClassData && (
        <>
          {/* Attributes */}
          <div className="flex flex-col gap-2">
            <Label className="text-xs text-muted-foreground font-semibold">Attributes</Label>
            {attributes.map((attr, i) => (
              <div key={i} className="flex items-center gap-1.5">
                <span data-testid={`uml-attribute-${i}`} className="text-foreground text-[13px] flex-1">{attr}</span>
                <Button
                  data-testid={`uml-remove-attribute-${i}`}
                  variant="outline"
                  size="icon-xs"
                  onClick={() => handleRemoveAttribute(i)}
                  className="text-destructive text-[11px]"
                >
                  ✕
                </Button>
              </div>
            ))}
            <div className="flex gap-1.5">
              <Input
                data-testid="uml-new-attribute"
                type="text"
                placeholder="New attribute..."
                value={newAttribute}
                onChange={(e) => setNewAttribute(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleAddAttribute(); }}
                className="flex-1"
              />
              <Button
                data-testid="uml-add-attribute"
                variant="outline"
                size="icon"
                onClick={handleAddAttribute}
                className="text-green-400 text-base"
              >
                +
              </Button>
            </div>
          </div>

          {/* Methods */}
          <div className="flex flex-col gap-2">
            <Label className="text-xs text-muted-foreground font-semibold">Methods</Label>
            {methods.map((method, i) => (
              <div key={i} className="flex items-center gap-1.5">
                <span data-testid={`uml-method-${i}`} className="text-foreground text-[13px] flex-1">{method}</span>
                <Button
                  data-testid={`uml-remove-method-${i}`}
                  variant="outline"
                  size="icon-xs"
                  onClick={() => handleRemoveMethod(i)}
                  className="text-destructive text-[11px]"
                >
                  ✕
                </Button>
              </div>
            ))}
            <div className="flex gap-1.5">
              <Input
                data-testid="uml-new-method"
                type="text"
                placeholder="New method..."
                value={newMethod}
                onChange={(e) => setNewMethod(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleAddMethod(); }}
                className="flex-1"
              />
              <Button
                data-testid="uml-add-method"
                variant="outline"
                size="icon"
                onClick={handleAddMethod}
                className="text-green-400 text-base"
              >
                +
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
