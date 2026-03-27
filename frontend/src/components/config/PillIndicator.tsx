'use client';

import { useState } from 'react';

interface PillIndicatorProps {
  expanded: boolean;
  onClick: () => void;
}

export default function PillIndicator({ expanded, onClick }: PillIndicatorProps) {
  const [hovered, setHovered] = useState(false);

  return (
    <button
      data-testid="pill-indicator"
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      aria-label={expanded ? 'Collapse panel' : 'Expand panel'}
      style={{
        width: hovered ? 64 : 40,
        height: hovered ? 6 : 4,
        borderRadius: 3,
        backgroundColor: hovered ? 'rgba(255, 255, 255, 0.6)' : 'rgba(255, 255, 255, 0.4)',
        border: 'none',
        padding: 0,
        cursor: 'pointer',
        display: 'block',
        transition: 'width 0.15s ease, height 0.15s ease, background-color 0.15s ease',
      }}
    />
  );
}
