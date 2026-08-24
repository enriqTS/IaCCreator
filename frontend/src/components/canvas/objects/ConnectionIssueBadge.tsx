'use client';

import { useConnectionIssues } from '@/hooks/useConnectionIssues';
import type { LineObject } from '@/types/diagram';

interface ConnectionIssueBadgeProps {
  line: LineObject;
  x: number;
  y: number;
}

/**
 * Marks a connection the backend reported as incomplete.
 *
 * The overlay is dismissed and gone, so the canvas is the only lasting sign
 * that a connection generates valid Terraform that cannot actually work.
 */
export default function ConnectionIssueBadge({ line, x, y }: ConnectionIssueBadgeProps) {
  const issues = useConnectionIssues(line);
  if (issues.length === 0) return null;

  return (
    <g data-testid={`connection-issue-badge-${line.id}`} className="cursor-pointer">
      <title>{issues.map((issue) => issue.message).join('\n')}</title>
      <circle cx={x} cy={y} r={7} fill="#f59e0b" stroke="#1f2937" strokeWidth={1.5} />
      <text
        x={x}
        y={y + 3.5}
        textAnchor="middle"
        fontSize="10"
        fontWeight="bold"
        fill="#1f2937"
        style={{ userSelect: 'none', pointerEvents: 'none' }}
      >
        !
      </text>
    </g>
  );
}
