/**
 * Centralized API client for all backend communication.
 *
 * Every method returns an ApiResult<T> discriminated union so callers
 * get type-safe success/error handling without try/catch.
 */

import type { DiagramSummary, ApiResult } from '@/types/api';
import type { ArchitectureDescription, DiagramState } from '@/types/serialization';

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
  /** POST /api/diagrams — create a new diagram, returns its id. */
  saveDiagram(state: DiagramState): Promise<ApiResult<{ id: string }>> {
    return request('/api/diagrams', {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify(state),
    }, (res) => res.json() as Promise<{ id: string }>);
  },

  /** PUT /api/diagrams/{id} — update an existing diagram. */
  updateDiagram(id: string, state: DiagramState): Promise<ApiResult<void>> {
    return request('/api/diagrams/' + encodeURIComponent(id), {
      method: 'PUT',
      headers: jsonHeaders(),
      body: JSON.stringify(state),
    }, async () => undefined as void);
  },

  /** GET /api/diagrams — list diagram summaries for the current session. */
  listDiagrams(): Promise<ApiResult<DiagramSummary[]>> {
    return request('/api/diagrams', {
      method: 'GET',
    }, (res) => res.json() as Promise<DiagramSummary[]>);
  },

  /** GET /api/diagrams/{id} — load full diagram state. */
  loadDiagram(id: string): Promise<ApiResult<any>> {
    return request('/api/diagrams/' + encodeURIComponent(id), {
      method: 'GET',
    }, (res) => res.json());
  },

  /** DELETE /api/diagrams/{id} — delete a diagram. */
  deleteDiagram(id: string): Promise<ApiResult<void>> {
    return request('/api/diagrams/' + encodeURIComponent(id), {
      method: 'DELETE',
    }, async () => undefined as void);
  },

  /** POST /generate/zip — generate Terraform from an architecture description. */
  generateTerraform(
    arch: ArchitectureDescription,
  ): Promise<ApiResult<Blob>> {
    return request('/generate/zip', {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify(arch),
    }, (res) => res.blob());
  },
};
