'use client';

import type { AlignmentGuide } from '@/utils/snap';

interface AlignmentGuidesProps {
  guides: AlignmentGuide[];
}

export default function AlignmentGuides({ guides }: AlignmentGuidesProps) {
  if (guides.length === 0) return null;

  return (
    <svg
      data-testid="alignment-guides-overlay"
      className="absolute inset-0 h-full w-full overflow-visible pointer-events-none"
    >
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
    </svg>
  );
}
