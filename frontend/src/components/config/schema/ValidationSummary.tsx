'use client';

import { AlertTriangle } from 'lucide-react';

export interface ValidationIssue {
  /** The field the issue belongs to, so the panel can open and focus it. */
  key: string;
  label: string;
  group: string;
}

interface ValidationSummaryProps {
  issues: ValidationIssue[];
  onSelect: (issue: ValidationIssue) => void;
}

/** Names the invalid fields, because tabs hide the ones you are not looking at. */
export default function ValidationSummary({ issues, onSelect }: ValidationSummaryProps) {
  if (issues.length === 0) return null;

  return (
    <div
      data-testid="validation-error-summary"
      className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2"
    >
      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" />
      <div className="flex flex-col gap-1">
        <span className="text-xs">
          {issues.length === 1 ? '1 field needs attention' : `${issues.length} fields need attention`}
        </span>
        <div className="flex flex-wrap gap-x-3 gap-y-1">
          {issues.map((issue) => (
            <button
              key={issue.key}
              type="button"
              data-testid={`validation-jump-${issue.key}`}
              onClick={() => onSelect(issue)}
              className="text-xs underline underline-offset-2 hover:text-foreground"
            >
              {issue.label}
              <span className="text-muted-foreground"> ({issue.group})</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
