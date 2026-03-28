'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface PillIndicatorProps {
  expanded: boolean;
  onClick: () => void;
}

export default function PillIndicator({ expanded, onClick }: PillIndicatorProps) {
  const [hovered, setHovered] = useState(false);

  return (
    <Button
      data-testid="pill-indicator"
      variant="ghost"
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      aria-label={expanded ? 'Collapse panel' : 'Expand panel'}
      className="px-5 py-3 border-none bg-transparent"
    >
      {/* Visible pill */}
      <span
        className={cn(
          'block rounded transition-all duration-150 ease-in-out pointer-events-none',
          hovered
            ? 'w-20 h-2 bg-white/65'
            : 'w-10 h-1 bg-white/40'
        )}
      />
    </Button>
  );
}
