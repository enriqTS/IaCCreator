'use client';

import { useState } from 'react';
import type { TextObject } from '@/types/diagram';
import { MIN_OBJECT_WIDTH, MIN_OBJECT_HEIGHT } from '@/types/diagram';
import { useDiagramStore } from '@/store/diagram-store';
import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';

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
    <div data-testid="text-visual-config" className="flex flex-wrap gap-3 items-end">
      <div className="flex flex-col gap-1 text-[13px]">
        <Label className="text-xs text-muted-foreground">Width (px)</Label>
        <Input
          data-testid="text-width"
          type="text"
          inputMode="numeric"
          value={localWidth}
          onChange={handleWidthChange}
          onBlur={handleWidthBlur}
          className="w-[140px]"
        />
      </div>

      <div className="flex flex-col gap-1 text-[13px]">
        <Label className="text-xs text-muted-foreground">Height (px)</Label>
        <Input
          data-testid="text-height"
          type="text"
          inputMode="numeric"
          value={localHeight}
          onChange={handleHeightChange}
          onBlur={handleHeightBlur}
          className="w-[140px]"
        />
      </div>

      <div className="flex flex-col gap-1 text-[13px]">
        <Label className="text-xs text-muted-foreground">Font Size</Label>
        <Input
          data-testid="text-font-size"
          type="text"
          inputMode="numeric"
          value={localFontSize}
          onChange={handleFontSizeChange}
          onBlur={handleFontSizeBlur}
          className="w-[140px]"
        />
      </div>

      <div className="flex flex-col gap-1 text-[13px]">
        <Label className="text-xs text-muted-foreground">Font Color</Label>
        <input
          data-testid="text-font-color"
          type="color"
          value={object.visualConfig.fontColor}
          onChange={handleFontColorChange}
          className="w-12 h-9 p-0.5 cursor-pointer rounded-md border border-input bg-transparent"
        />
      </div>

      <div className="flex flex-col gap-1 text-[13px]">
        <Label className="text-xs text-muted-foreground">Alignment</Label>
        <div className="flex gap-1">
          {(['left', 'center', 'right'] as const).map((align) => (
            <Button
              key={align}
              data-testid={`text-align-${align}`}
              variant="outline"
              size="icon"
              onClick={() => handleTextAlignChange(align)}
              className={cn(
                'size-8 text-[13px]',
                object.visualConfig.textAlign === align && 'bg-blue-500/30'
              )}
            >
              {align === 'left' ? '⫷' : align === 'center' ? '☰' : '⫸'}
            </Button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-1 text-[13px]">
        <Label className="text-xs text-muted-foreground">Style</Label>
        <div className="flex gap-1">
          <Button
            data-testid="text-bold"
            variant="outline"
            size="icon"
            onClick={handleBoldToggle}
            className={cn(
              'size-8 text-[13px] font-bold',
              object.visualConfig.bold && 'bg-blue-500/30'
            )}
          >
            B
          </Button>
          <Button
            data-testid="text-italic"
            variant="outline"
            size="icon"
            onClick={handleItalicToggle}
            className={cn(
              'size-8 text-[13px] italic',
              object.visualConfig.italic && 'bg-blue-500/30'
            )}
          >
            I
          </Button>
        </div>
      </div>
    </div>
  );
}
