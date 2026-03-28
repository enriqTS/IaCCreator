'use client';

import { useState } from 'react';
import type { ArchitectureBlock } from '@/types/diagram';
import { MIN_OBJECT_WIDTH, MIN_OBJECT_HEIGHT } from '@/types/diagram';
import { useDiagramStore } from '@/store/diagram-store';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

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
    <div data-testid="block-visual-config" className="flex flex-wrap gap-3 items-end">
      <div className="flex flex-col gap-1.5">
        <Label className="text-xs text-muted-foreground">Width (px)</Label>
        <Input
          data-testid="block-width"
          type="text"
          inputMode="numeric"
          value={localWidth}
          onChange={handleWidthChange}
          onBlur={handleWidthBlur}
          className="w-[140px]"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label className="text-xs text-muted-foreground">Height (px)</Label>
        <Input
          data-testid="block-height"
          type="text"
          inputMode="numeric"
          value={localHeight}
          onChange={handleHeightChange}
          onBlur={handleHeightBlur}
          className="w-[140px]"
        />
      </div>
    </div>
  );
}
