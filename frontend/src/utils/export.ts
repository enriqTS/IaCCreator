/**
 * Export utility — serializes diagram state and sends to the backend
 * /generate/zip endpoint via the API client, triggering a browser download
 * of the resulting ZIP.
 */

import type { DiagramElement } from '@/types/diagram';
import type { ArchitectureDescription } from '@/types/serialization';
import { apiClient } from '@/utils/api-client';

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
 * Export the current diagram to Terraform via the API client.
 *
 * 1. Rejects empty diagrams (no elements).
 * 2. Validates required config fields per service type.
 * 3. Serializes to ArchitectureDescription and calls apiClient.generateTerraform.
 * 4. On success — triggers browser download of `terraform.zip`.
 * 5. On HTTP error (422/500/etc) — maps to ExportResult with appropriate errors.
 * 6. On network failure — returns a network error message.
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

  // 4. Call API client
  const result = await apiClient.generateTerraform(payload);

  if (result.ok) {
    triggerDownload(result.data, 'terraform.zip');
    return { success: true };
  }

  // 5. Map ApiError to ExportResult
  const { error } = result;

  if (error.type === 'network') {
    return {
      success: false,
      error: 'Network error: unable to reach the server. Please check your connection and try again.',
    };
  }

  // HTTP errors
  if (error.status === 422) {
    return {
      success: false,
      error: 'Validation error from server',
      fieldErrors: error.fieldErrors ?? { detail: 'Validation error' },
    };
  }

  return {
    success: false,
    error: error.message,
  };
}
