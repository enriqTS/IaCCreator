'use client';

interface PillIndicatorProps {
  expanded: boolean;
  onClick: () => void;
}

export default function PillIndicator({ expanded, onClick }: PillIndicatorProps) {
  return (
    <button
      data-testid="pill-indicator"
      onClick={onClick}
      aria-label={expanded ? 'Collapse panel' : 'Expand panel'}
      style={{
        width: 40,
        height: 4,
        borderRadius: 2,
        backgroundColor: 'rgba(255, 255, 255, 0.4)',
        border: 'none',
        padding: 0,
        cursor: 'pointer',
        display: 'block',
      }}
    />
  );
}
