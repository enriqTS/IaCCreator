'use client';

import type { AlignmentGuide, DistributionGuide } from '@/utils/snap';

interface AlignmentGuidesProps {
  guides: AlignmentGuide[];
  distributionGuides?: DistributionGuide[];
}

export default function AlignmentGuides({ guides, distributionGuides = [] }: AlignmentGuidesProps) {
  if (guides.length === 0 && distributionGuides.length === 0) return null;

  return (
    <svg
      data-testid="alignment-guides-overlay"
      className="absolute inset-0 h-full w-full overflow-visible pointer-events-none"
    >
      {/* Alignment guide lines */}
      {guides.map((guide, index) => {
        const key = `${guide.axis}-${guide.position}-${guide.from}-${guide.to}-${index}`;

        if (guide.axis === 'horizontal') {
          return (
            <line
              key={key}
              x1={guide.from}
              y1={guide.position}
              x2={guide.to}
              y2={guide.position}
              stroke="#f472b6"
              strokeDasharray="4 2"
              strokeWidth={1}
            />
          );
        }

        return (
          <line
            key={key}
            x1={guide.position}
            y1={guide.from}
            x2={guide.position}
            y2={guide.to}
            stroke="#f472b6"
            strokeDasharray="4 2"
            strokeWidth={1}
          />
        );
      })}

      {/* Distribution (equal-spacing) indicators */}
      {distributionGuides.map((dGuide, dIdx) =>
        dGuide.segments.map((seg, sIdx) => {
          const key = `dist-${dGuide.axis}-${dIdx}-${sIdx}`;
          const midPoint = (seg.from + seg.to) / 2;
          const gap = Math.round(dGuide.gap);

          if (dGuide.axis === 'horizontal') {
            // Horizontal distribution: spacing indicators are horizontal arrows
            return (
              <g key={key}>
                {/* Spacing line */}
                <line
                  x1={seg.from}
                  y1={seg.crossPosition}
                  x2={seg.to}
                  y2={seg.crossPosition}
                  stroke="#a78bfa"
                  strokeWidth={1}
                />
                {/* Left tick */}
                <line
                  x1={seg.from}
                  y1={seg.crossPosition - 4}
                  x2={seg.from}
                  y2={seg.crossPosition + 4}
                  stroke="#a78bfa"
                  strokeWidth={1}
                />
                {/* Right tick */}
                <line
                  x1={seg.to}
                  y1={seg.crossPosition - 4}
                  x2={seg.to}
                  y2={seg.crossPosition + 4}
                  stroke="#a78bfa"
                  strokeWidth={1}
                />
                {/* Gap label */}
                <text
                  x={midPoint}
                  y={seg.crossPosition - 6}
                  textAnchor="middle"
                  fontSize={9}
                  fill="#a78bfa"
                  fontFamily="monospace"
                >
                  {gap}
                </text>
              </g>
            );
          } else {
            // Vertical distribution: spacing indicators are vertical arrows
            return (
              <g key={key}>
                {/* Spacing line */}
                <line
                  x1={seg.crossPosition}
                  y1={seg.from}
                  x2={seg.crossPosition}
                  y2={seg.to}
                  stroke="#a78bfa"
                  strokeWidth={1}
                />
                {/* Top tick */}
                <line
                  x1={seg.crossPosition - 4}
                  y1={seg.from}
                  x2={seg.crossPosition + 4}
                  y2={seg.from}
                  stroke="#a78bfa"
                  strokeWidth={1}
                />
                {/* Bottom tick */}
                <line
                  x1={seg.crossPosition - 4}
                  y1={seg.to}
                  x2={seg.crossPosition + 4}
                  y2={seg.to}
                  stroke="#a78bfa"
                  strokeWidth={1}
                />
                {/* Gap label */}
                <text
                  x={seg.crossPosition + 8}
                  y={midPoint + 3}
                  textAnchor="start"
                  fontSize={9}
                  fill="#a78bfa"
                  fontFamily="monospace"
                >
                  {gap}
                </text>
              </g>
            );
          }
        }),
      )}
    </svg>
  );
}
