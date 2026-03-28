'use client';

import { useState } from 'react';
import type { GeometricObject, GeometricShape } from '@/types/diagram';
import { MIN_OBJECT_WIDTH, MIN_OBJECT_HEIGHT } from '@/types/diagram';
import { useDiagramStore } from '@/store/diagram-store';
import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

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

  const handleFillToggle = (checked: boolean | 'indeterminate') => {
    updateVisualConfig(object.id, { fill: checked === true });
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

  const handleShapeChange = (value: string) => {
    updateVisualConfig(object.id, { shape: value as GeometricShape });
  };

  return (
    <div data-testid="geo-visual-config" className="flex flex-wrap gap-3 items-end">
      <div className="flex flex-col gap-1 text-[13px]">
        <Label className="text-xs text-muted-foreground">Width (px)</Label>
        <Input
          data-testid="geo-width"
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
          data-testid="geo-height"
          type="text"
          inputMode="numeric"
          value={localHeight}
          onChange={handleHeightChange}
          onBlur={handleHeightBlur}
          className="w-[140px]"
        />
      </div>

      <div className="flex items-center gap-1.5">
        <Checkbox
          data-testid="geo-fill-toggle"
          checked={object.visualConfig.fill}
          onCheckedChange={handleFillToggle}
        />
        <Label className="text-xs text-muted-foreground">Fill</Label>
      </div>

      <div className="flex flex-col gap-1 text-[13px]">
        <Label className="text-xs text-muted-foreground">Fill Color</Label>
        <input
          data-testid="geo-fill-color"
          type="color"
          value={object.visualConfig.fillColor}
          onChange={handleFillColorChange}
          disabled={!object.visualConfig.fill}
          className={cn(
            'w-12 h-9 p-0.5 rounded-md border border-input bg-transparent',
            object.visualConfig.fill ? 'cursor-pointer opacity-100' : 'cursor-not-allowed opacity-40'
          )}
        />
      </div>

      <div className="flex flex-col gap-1 text-[13px]">
        <Label className="text-xs text-muted-foreground">Border Color</Label>
        <input
          data-testid="geo-border-color"
          type="color"
          value={object.visualConfig.borderColor}
          onChange={handleBorderColorChange}
          className="w-12 h-9 p-0.5 cursor-pointer rounded-md border border-input bg-transparent"
        />
      </div>

      <div className="flex flex-col gap-1 text-[13px]">
        <Label className="text-xs text-muted-foreground">Border Width</Label>
        <Input
          data-testid="geo-border-width"
          type="text"
          inputMode="numeric"
          value={object.visualConfig.borderWidth}
          onChange={handleBorderWidthChange}
          className="w-[140px]"
        />
      </div>

      <div className="flex flex-col gap-1 text-[13px]">
        <Label className="text-xs text-muted-foreground">Shape</Label>
        <Select
          value={object.visualConfig.shape}
          onValueChange={handleShapeChange}
        >
          <SelectTrigger data-testid="geo-shape" className="w-[140px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="rectangle">Rectangle</SelectItem>
            <SelectItem value="ellipse">Ellipse</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
