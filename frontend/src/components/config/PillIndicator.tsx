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
        // The visible pill is small, but the clickable area is always generous
        width: hovered ? 80 : 40,
        height: hovered ? 8 : 4,
        borderRadius: 4,
        backgroundColor: hovered ? 'rgba(255, 255, 255, 0.65)' : 'rgba(255, 255, 255, 0.4)',
        border: 'none',
        // Large padding creates a big invisible hit area around the pill
        padding: '12px 20px',
        backgroundClip: 'content-box',
        cursor: 'pointer',
        display: 'block',
        transition: 'width 0.15s ease, height 0.15s ease, background-color 0.15s ease',
        boxSizing: 'content-box',
      }}
    />
  );
}
