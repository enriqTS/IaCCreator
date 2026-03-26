/**
 * Export utility — serializes diagram state and POSTs to the backend
 * /generate/zip endpoint, triggering a browser download of the resulting ZIP.
 */

import type { DiagramElement } from '@/types/diagram';
import type { ArchitectureDescription } from '@/types/serialization';

export interface ExportResult {
  success: boolean;
  error?: string;
  fieldErrors?: Record<string, string>;
}

/**
 * Required config fields per service type.
 * Only service types with mandatory fields are listed.
 */
const REQUIRED_FIELDS: Record<string, string[]> = {
  dynamodb: ['hash_key'],
};

/**
 * Validate that every element has its required config fields populated.
 * Returns a map of `elementName.fieldName` → error message for any violations.
 */
function validateRequiredFields(
  elements: Map<string, DiagramElement>,
): Record<string, string> | null {
  const errors: Record<string, string> = {};

  for (const el of elements.values()) {
    const required = REQUIRED_FIELDS[el.serviceType];
    if (!required) continue;

    for (const field of required) {
      const value = (el.config as Record<string, unknown>)[field];
      if (value === undefined || value === null || value === '') {
        errors[`${el.name}.${field}`] = `${el.name}: "${field}" is required for ${el.serviceType}`;
      }
    }
  }

  return Object.keys(errors).length > 0 ? errors : null;
}

/**
 * Trigger a browser file download from a Blob.
 */
function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Export the current diagram to Terraform by POSTing to the backend.
 *
 * 1. Rejects empty diagrams (no elements).
 * 2. Validates required config fields per service type.
 * 3. Serializes to ArchitectureDescription and POSTs to `/generate/zip`.
 * 4. On 200 — triggers browser download of `terraform.zip`.
 * 5. On 422 — parses field-level validation errors.
 * 6. On 500 — returns a generic server error.
 * 7. On network failure — returns a network error message.
 */
export async function exportToTerraform(
  serializeToArchitectureDescription: () => ArchitectureDescription,
  elements: Map<string, DiagramElement>,
): Promise<ExportResult> {
  // 1. Reject empty diagrams
  if (elements.size === 0) {
    return { success: false, error: 'No elements in diagram' };
  }

  // 2. Validate required config fields
  const fieldErrors = validateRequiredFields(elements);
  if (fieldErrors) {
    return { success: false, error: 'Validation failed', fieldErrors };
  }

  // 3. Serialize
  const payload = serializeToArchitectureDescription();

  // 4. POST to backend
  try {
    const response = await fetch('/generate/zip', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (response.ok) {
      const blob = await response.blob();
      triggerDownload(blob, 'terraform.zip');
      return { success: true };
    }

    // 5. Handle 422 validation errors
    if (response.status === 422) {
      try {
        const body = await response.json();
        const parsed: Record<string, string> = {};
        if (body.detail && Array.isArray(body.detail)) {
          for (const err of body.detail) {
            const loc = Array.isArray(err.loc) ? err.loc.join('.') : String(err.loc ?? 'unknown');
            parsed[loc] = String(err.msg ?? err.message ?? 'Validation error');
          }
        } else if (body.detail && typeof body.detail === 'string') {
          parsed['detail'] = body.detail;
        }
        return {
          success: false,
          error: 'Validation error from server',
          fieldErrors: Object.keys(parsed).length > 0 ? parsed : { detail: 'Validation error' },
        };
      } catch {
        return { success: false, error: 'Validation error from server' };
      }
    }

    // 6. Handle 500 and other server errors
    try {
      const body = await response.json();
      const detail = typeof body.detail === 'string' ? body.detail : 'Server error';
      return { success: false, error: detail };
    } catch {
      return { success: false, error: `Server error (${response.status})` };
    }
  } catch {
    // 7. Network error
    return { success: false, error: 'Network error: unable to reach the server. Please check your connection and try again.' };
  }
}
