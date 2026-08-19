/**
 * Export utility — serializes diagram state and sends to the backend
 * /generate/zip endpoint via the API client, triggering a browser download
 * of the resulting ZIP.
 */

import type { ArchitectureBlock, CanvasObject } from '@/types/diagram';
import type { ArchitectureDescription } from '@/types/serialization';
import { getSchemas } from '@/store/schema-store';
import { apiClient } from '@/utils/api-client';

export interface ExportResult {
  success: boolean;
  error?: string;
  fieldErrors?: Record<string, string>;
}

/** Fields the backend validates even on an otherwise untouched block. */
const ALWAYS_REQUIRED: Record<string, string[]> = {
  dynamodb: ['hash_key'],
};

/** Required config fields come from the schema the backend serves. */
function requiredFieldsFor(serviceType: string): string[] {
  return (getSchemas()[serviceType] ?? [])
    .filter((entry) => entry.required)
    .map((entry) => entry.name);
}

/**
 * Extract architecture blocks from the canvas objects map.
 */
function getArchitectureBlocks(
  canvasObjects: Map<string, CanvasObject>,
): ArchitectureBlock[] {
  return Array.from(canvasObjects.values()).filter(
    (obj): obj is ArchitectureBlock => obj.objectType === 'architecture-block',
  );
}

/**
 * Validate that every architecture block has its required config fields populated.
 * Returns a map of `blockName.fieldName` → error message for any violations.
 */
function validateRequiredFields(
  blocks: ArchitectureBlock[],
): Record<string, string> | null {
  const errors: Record<string, string> = {};

  for (const block of blocks) {
    const config = block.config as Record<string, unknown>;
    // Mirror the backend: it applies a service's typed config only once the block has
    // been configured, but ResourceInstance.validate_dynamodb_hash_key always runs.
    const configured = Object.keys(config).length > 0;
    const required = configured
      ? requiredFieldsFor(block.serviceType)
      : ALWAYS_REQUIRED[block.serviceType] ?? [];
    if (required.length === 0) continue;

    for (const field of required) {
      const value = config[field];
      if (value === undefined || value === null || value === '') {
        errors[`${block.name}.${field}`] = `${block.name}: "${field}" is required for ${block.serviceType}`;
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
  canvasObjects: Map<string, CanvasObject>,
): Promise<ExportResult> {
  // 1. Extract architecture blocks and reject empty diagrams
  const blocks = getArchitectureBlocks(canvasObjects);
  if (blocks.length === 0) {
    return { success: false, error: 'No elements in diagram' };
  }

  // 2. Validate required config fields
  const fieldErrors = validateRequiredFields(blocks);
  if (fieldErrors) {
    return { success: false, error: 'Validation failed', fieldErrors };
  }

  // 3. Serialize
  const payload = serializeToArchitectureDescription();

  // 4. Call API client
  const result = await apiClient.generateTerraform(payload);

  if (result.ok) {
    const filename = `${payload.project_name || 'terraform'}.zip`;
    triggerDownload(result.data, filename);
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
