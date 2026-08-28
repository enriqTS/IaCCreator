/**
 * Centralized API client for all backend communication.
 *
 * Every method returns an ApiResult<T> discriminated union so callers
 * get type-safe success/error handling without try/catch.
 */

import type { DiagramSummary, ApiResult } from '@/types/api';
import type { ConnectionPreviewResponse } from '@/types/connection-preview';
import type { DiagramState } from '@/types/serialization';
import type { GlobalTerraformConfig, ServiceVariableSchemas } from '@/types/terraform-variables';
import type { ApiConnection } from '@/connections/schema-store';
import type { NamingRulesPayload } from '@/store/naming-store';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? '';

/**
 * Parse Pydantic 422 validation error details into a flat fieldErrors map.
 */
function parsePydanticErrors(
  detail: unknown,
): Record<string, string> | undefined {
  if (!Array.isArray(detail)) return undefined;
  const errors: Record<string, string> = {};
  for (const err of detail) {
    const loc = Array.isArray(err.loc)
      ? err.loc.join('.')
      : String(err.loc ?? 'unknown');
    errors[loc] = String(err.msg ?? err.message ?? 'Validation error');
  }
  return Object.keys(errors).length > 0 ? errors : undefined;
}

/**
 * Shared request helper. Wraps fetch with credentials and structured errors.
 */
async function request<T>(
  path: string,
  init: RequestInit,
  parseBody: (res: Response) => Promise<T>,
): Promise<ApiResult<T>> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      credentials: 'include',
    });
  } catch (err: unknown) {
    return {
      ok: false,
      error: {
        type: 'network',
        message:
          err instanceof Error ? err.message : 'Network request failed',
      },
    };
  }

  if (response.ok) {
    const data = await parseBody(response);
    return { ok: true, data };
  }

  // Non-success — build an http error
  let message = `HTTP ${response.status}`;
  let fieldErrors: Record<string, string> | undefined;

  try {
    const body = await response.json();
    if (response.status === 422) {
      fieldErrors = parsePydanticErrors(body.detail);
    }
    if (typeof body.detail === 'string') {
      message = body.detail;
    } else if (fieldErrors) {
      message = 'Validation error';
    }
  } catch {
    // body wasn't JSON — keep the default message
  }

  return {
    ok: false,
    error: {
      type: 'http',
      status: response.status,
      message,
      ...(fieldErrors ? { fieldErrors } : {}),
    },
  };
}

function jsonHeaders(): HeadersInit {
  return { 'Content-Type': 'application/json' };
}

export const apiClient = {
  /** GET /api/editor-bootstrap — load backend-owned editor metadata. */
  getEditorBootstrap(): Promise<ApiResult<{
    services: {
      service_type: string;
      display_name: string;
      category: string;
      classification: 'resource' | 'capability' | 'composite' | 'decorative' | 'legacy';
      lifecycle: 'active' | 'deprecated' | 'retired' | 'decorative';
      capabilities: {
        diagram: boolean;
        terraform: boolean;
        configurable: boolean;
        connectable: boolean;
      };
    }[];
    variable_schemas: ServiceVariableSchemas;
    connection_schemas: ApiConnection[];
    naming_rules: NamingRulesPayload;
    global_terraform_defaults: GlobalTerraformConfig;
    diagram_version: number;
    containment?: {
      container_types: { container_type: string; display_name: string; allowed_parent_types: string[]; allowed_child_types: string[]; config_fields: string[] }[];
      service_capabilities: { service_type: string; container_presentation: boolean; allowed_parent_types: string[]; allowed_child_types: string[]; allowed_lifecycles: string[] }[];
      rules: { child_type: string; parent_type: string; resolved_ancestor_type?: string | null; connection_type?: string | null; inherited_fields: string[]; outcome: 'terraform-connection' | 'inherited-scope' | 'visual-only' }[];
      inherited_fields: { field: string; source_types: string[]; target_types: string[]; policy: 'managed' | 'overridable' | 'external-fallback' }[];
    };
  }>> {
    return request('/api/editor-bootstrap', { method: 'GET' }, (res) => res.json());
  },

  /** POST /api/diagrams/normalize — canonicalize editor domain state. */
  normalizeDiagram(diagram: DiagramState): Promise<ApiResult<DiagramState>> {
    return request('/api/diagrams/normalize', {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify(diagram),
    }, (res) => res.json());
  },

  /** POST /api/diagrams/connections/apply — materialize linked connection intent. */
  applyConnectionOperation(
    diagram: DiagramState,
    operation: Record<string, unknown>,
  ): Promise<ApiResult<DiagramState>> {
    return request('/api/diagrams/connections/apply', {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify({ diagram, operation }),
    }, (res) => res.json());
  },

  /** POST /api/diagrams/containment/resolve — inspect effective semantic outcomes. */
  resolveContainment(diagram: DiagramState): Promise<ApiResult<{
    effective_scopes: { object_id: string; region?: string | null; availability_zone?: string | null; vpc_id?: string | null; subnet_id?: string | null }[];
    environment_scopes: { environment: string; effective_scopes: { object_id: string; region?: string | null; availability_zone?: string | null; vpc_id?: string | null; subnet_id?: string | null }[] }[];
    derived_connections: { connector_id: string; source_id: string; target_id: string; connection_type: string; container_id: string }[];
    inherited_values: { object_id: string; field: string; value: unknown; source_id: string; policy: 'managed' | 'overridable' | 'external-fallback' }[];
    issues: { code: string; message: string; object_id?: string | null; parent_id?: string | null; severity: 'error' | 'warning' }[];
  }>> {
    return request('/api/diagrams/containment/resolve', {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify(diagram),
    }, (res) => res.json());
  },

  /** POST /api/diagrams/containment/apply — validate semantic hierarchy intent. */
  applyContainmentOperation(
    diagram: DiagramState,
    operation: Record<string, unknown>,
  ): Promise<ApiResult<{ diagram: DiagramState; resolution: Record<string, unknown> }>> {
    return request('/api/diagrams/containment/apply', {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify({ diagram, operation }),
    }, (res) => res.json());
  },

  /** POST /api/resources/initialize — derive backend-owned resource defaults. */
  initializeResource(
    serviceType: string,
    existingNames: string[],
  ): Promise<ApiResult<{ name: string; config: Record<string, unknown>; terraform_variables: Record<string, string | number | boolean> }>> {
    return request('/api/resources/initialize', {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify({ service_type: serviceType, existing_names: existingNames }),
    }, (res) => res.json());
  },

  /** POST /api/diagrams — create a new diagram, returns its id. */
  saveDiagram(state: DiagramState): Promise<ApiResult<{ id: string }>> {
    return request('/api/diagrams', {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify(state),
    }, (res) => res.json() as Promise<{ id: string }>);
  },

  /** PUT /api/diagrams/{id} — update an existing diagram. */
  updateDiagram(id: string, state: DiagramState): Promise<ApiResult<{ id: string }>> {
    return request('/api/diagrams/' + encodeURIComponent(id), {
      method: 'PUT',
      headers: jsonHeaders(),
      body: JSON.stringify(state),
    }, (res) => res.json() as Promise<{ id: string }>);
  },

  /** GET /api/diagrams — list diagram summaries for the current session. */
  listDiagrams(): Promise<ApiResult<DiagramSummary[]>> {
    return request('/api/diagrams', {
      method: 'GET',
    }, (res) => res.json() as Promise<DiagramSummary[]>);
  },

  /** GET /api/diagrams/{id} — load full diagram state. */
  loadDiagram(id: string): Promise<ApiResult<DiagramState>> {
    return request('/api/diagrams/' + encodeURIComponent(id), {
      method: 'GET',
    }, (res) => res.json() as Promise<DiagramState>);
  },

  /** DELETE /api/diagrams/{id} — delete a diagram. */
  deleteDiagram(id: string): Promise<ApiResult<void>> {
    return request('/api/diagrams/' + encodeURIComponent(id), {
      method: 'DELETE',
    }, async () => undefined as void);
  },

  /** Preview diagram connections through backend conversion. */
  previewConnections(
    diagram: DiagramState,
  ): Promise<ApiResult<ConnectionPreviewResponse>> {
    return request('/api/diagrams/connections/preview', {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify(diagram),
    }, (res) => res.json() as Promise<ConnectionPreviewResponse>);
  },

  /** Import generation architecture JSON into canonical semantic canvas state. */
  importArchitecture(architecture: unknown): Promise<ApiResult<{
    diagram: DiagramState;
    imported_resource_count: number;
    inferred_container_count: number;
  }>> {
    return request('/api/import/architecture', {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify({ architecture }),
    }, (res) => res.json());
  },

  /** Generate Terraform directly from canonical diagram state. */
  generateTerraform(
    diagram: DiagramState,
  ): Promise<ApiResult<Blob>> {
    return request('/api/diagrams/generate/zip', {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify(diagram),
    }, (res) => res.blob());
  },
};
