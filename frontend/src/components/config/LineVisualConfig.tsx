'use client';

import type { LineObject, RoutingMode, StrokeStyle } from '@/types/diagram';
import { useDiagramStore } from '@/store/diagram-store';
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

  const handleStrokeStyleChange = (value: string) => {
    updateVisualConfig(object.id, { strokeStyle: value as StrokeStyle });
  };

  const handleRoutingModeChange = (value: string) => {
    updateVisualConfig(object.id, { routingMode: value as RoutingMode });
  };

  const handleStartArrowChange = (checked: boolean | 'indeterminate') => {
    updateVisualConfig(object.id, { startArrow: checked === true });
  };

  const handleEndArrowChange = (checked: boolean | 'indeterminate') => {
    updateVisualConfig(object.id, { endArrow: checked === true });
  };

  return (
    <div data-testid="line-visual-config" className="flex flex-wrap gap-3 items-end">
      <div className="flex flex-col gap-1 text-[13px]">
        <Label className="text-xs text-muted-foreground">Color</Label>
        <input
          data-testid="line-color"
          type="color"
          value={object.visualConfig.color}
          onChange={handleColorChange}
          className="w-12 h-9 p-0.5 cursor-pointer rounded-md border border-input bg-transparent"
        />
      </div>

      <div className="flex flex-col gap-1 text-[13px]">
        <Label className="text-xs text-muted-foreground">Border Width</Label>
        <Input
          data-testid="line-border-width"
          type="text"
          inputMode="numeric"
          value={object.visualConfig.borderWidth}
          onChange={handleBorderWidthChange}
          className="w-full"
        />
      </div>

      <div className="flex flex-col gap-1 text-[13px]">
        <Label className="text-xs text-muted-foreground">Stroke Style</Label>
        <Select
          value={object.visualConfig.strokeStyle}
          onValueChange={handleStrokeStyleChange}
        >
          <SelectTrigger data-testid="line-stroke-style" className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="solid">Solid</SelectItem>
            <SelectItem value="dashed">Dashed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-1 text-[13px]">
        <Label className="text-xs text-muted-foreground">Routing</Label>
        <Select
          value={object.visualConfig.routingMode}
          onValueChange={handleRoutingModeChange}
        >
          <SelectTrigger data-testid="line-routing-mode" className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="orthogonal">Orthogonal</SelectItem>
            <SelectItem value="diagonal">Diagonal</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="flex items-center gap-1.5">
        <Checkbox
          data-testid="line-start-arrow"
          checked={object.visualConfig.startArrow}
          onCheckedChange={handleStartArrowChange}
        />
        <Label className="text-xs text-muted-foreground">Start Arrow</Label>
      </div>

      <div className="flex items-center gap-1.5">
        <Checkbox
          data-testid="line-end-arrow"
          checked={object.visualConfig.endArrow}
          onCheckedChange={handleEndArrowChange}
        />
        <Label className="text-xs text-muted-foreground">End Arrow</Label>
      </div>
    </div>
  );
}
