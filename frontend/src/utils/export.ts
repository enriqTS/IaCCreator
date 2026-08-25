/** Browser download adapter for backend-owned diagram generation. */

import type { ArchitectureDescription, DiagramState } from '@/types/serialization';
import { apiClient } from '@/utils/api-client';

export interface ExportResult {
  success: boolean;
  error?: string;
  fieldErrors?: Record<string, string>;
}

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

export async function exportToTerraform(
  serializeDiagramState: () => DiagramState | ArchitectureDescription,
  _legacyCanvasObjects?: unknown,
): Promise<ExportResult> {
  const diagram = serializeDiagramState();
  const result = await apiClient.generateTerraform(diagram);
  if (result.ok) {
    const name = 'projectName' in diagram ? diagram.projectName : diagram.project_name;
    triggerDownload(result.data, `${name || 'terraform'}.zip`);
    return { success: true };
  }
  if (result.error.type === 'network') {
    return { success: false, error: `Network error: ${result.error.message}` };
  }
  if (result.error.status === 422) {
    return {
      success: false,
      error: 'Validation error from server',
      fieldErrors: result.error.fieldErrors ?? { detail: 'Validation error' },
    };
  }
  return { success: false, error: result.error.message };

}
