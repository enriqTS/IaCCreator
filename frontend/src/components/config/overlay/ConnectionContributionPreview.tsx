'use client';

import { useConnectionPreview, useConnectionPreviewStore } from '@/store/connection-preview-store';
import { Label } from '@/components/ui/label';
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

      <div className="flex flex-col gap-2">
        <Label className="text-xs font-semibold text-muted-foreground">
          Terraform resources
        </Label>
        {preview.resources.length > 0 ? (
          <ul data-testid="contribution-resources" className="flex flex-col gap-1">
            {preview.resources.map((resource) => (
              <li
                key={`${resource.module}.${resource.resource_type}.${resource.resource_name}`}
                className="font-mono text-xs text-foreground"
              >
                {resource.resource_type}
                <span className="text-muted-foreground">.{resource.resource_name}</span>
                <span className="text-muted-foreground"> — {resource.module}</span>
              </li>
            ))}
          </ul>
        ) : (
          <span className="text-xs text-muted-foreground">
            This connection emits no resources of its own.
          </span>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <Label className="text-xs font-semibold text-muted-foreground">IAM</Label>
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
      </div>
    </div>
  );
}
