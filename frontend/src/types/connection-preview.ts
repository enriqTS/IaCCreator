/**
 * Mirrors the backend's connection preview models. The backend decides what a
 * connection contributes and what is wrong with it; nothing here re-derives that.
 */

export interface PreviewResource {
  module: string;
  resource_type: string;
  resource_name: string;
}

export interface PreviewGrant {
  role_owner: string;
  effect: string;
  actions: string[];
  resources: string[];
}

export interface ConnectionIssue {
  severity: 'error' | 'warning';
  message: string;
}

export interface ConnectionPreview {
  source: string;
  target: string;
  source_id?: string | null;
  target_id?: string | null;
  connection_type: string;
  label: string;
  resources: PreviewResource[];
  iam: PreviewGrant[];
  issues: ConnectionIssue[];
}

export interface ConnectionPreviewResponse {
  previews: ConnectionPreview[];
}
