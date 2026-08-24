'use client';

import type { ReactNode } from 'react';
import { useConnectionPreview, useConnectionPreviewStore } from '@/store/connection-preview-store';
import { AlertTriangle } from 'lucide-react';

interface ConnectionContributionPreviewProps {
  connectorId: string;
}

/** Shows what a connection generates, as the backend reports it. */
export default function ConnectionContributionPreview({
  connectorId,
}: ConnectionContributionPreviewProps) {
  const preview = useConnectionPreview(connectorId);
  const status = useConnectionPreviewStore((s) => s.status);
  const error = useConnectionPreviewStore((s) => s.error);

  if (!preview) {
    return (
      <div data-testid="contribution-preview-empty" className="flex flex-col gap-1 py-2">
        <span className="text-xs text-muted-foreground">
          {status === 'loading'
            ? 'Working out what this connection generates…'
            : status === 'unavailable'
              ? `The backend could not preview this connection: ${error ?? 'unknown reason'}`
              : 'Nothing to preview for this connection yet.'}
        </span>
      </div>
    );
  }

  return (
    <div data-testid="contribution-preview" className="flex flex-col gap-4">
      {preview.issues.length > 0 && (
        <div data-testid="contribution-issues" className="flex flex-col gap-2">
          {preview.issues.map((issue, index) => (
            <div
              key={index}
              className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2"
            >
              <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-500" />
              <span className="text-xs text-foreground">{issue.message}</span>
            </div>
          ))}
        </div>
      )}

      <Section heading="Terraform resources" aside="module">
        {preview.resources.length > 0 ? (
          <ul data-testid="contribution-resources" className="border-t">
            {preview.resources.map((resource) => (
              <li
                key={`${resource.module}.${resource.resource_type}.${resource.resource_name}`}
                className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-4 border-b py-1 last:border-b-0"
              >
                <span className="truncate font-mono text-xs text-foreground">
                  {resource.resource_type}
                  <span className="text-muted-foreground">.{resource.resource_name}</span>
                </span>
                <span className="text-xs text-muted-foreground">{resource.module}</span>
              </li>
            ))}
          </ul>
        ) : (
          <span className="text-xs text-muted-foreground">
            This connection emits no resources of its own.
          </span>
        )}
      </Section>

      <Section heading="IAM">
        {preview.iam.length > 0 ? (
          <ul data-testid="contribution-iam" className="flex flex-col gap-2">
            {preview.iam.map((grant, index) => (
              <li key={index} className="flex flex-col gap-0.5">
                <span className="text-xs text-foreground">
                  {grant.effect} on {grant.role_owner}
                </span>
                <span className="font-mono text-xs text-muted-foreground">
                  {grant.actions.join(', ')}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <span className="text-xs text-muted-foreground">
            This connection grants no permissions.
          </span>
        )}
      </Section>
    </div>
  );
}

/** A titled block; the heading names the list rather than labelling a control. */
function Section({
  heading,
  aside,
  children,
}: {
  heading: string;
  aside?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between">
        <h3 className="text-xs font-semibold text-muted-foreground">{heading}</h3>
        {aside && <span className="text-xs text-muted-foreground">{aside}</span>}
      </div>
      {children}
    </div>
  );
}
