import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ImportArchitectureDialog from '@/components/menu/ImportArchitectureDialog';
import { useDiagramStore } from '@/store/diagram-store';
import { apiClient } from '@/utils/api-client';

const importedDiagram = {
  version: 4 as const,
  projectName: 'imported',
  environments: [],
  canvasObjects: [],
  connectors: [],
  objectGroups: [],
  viewport: { offsetX: 0, offsetY: 0, scale: 1 },
  globalRoutingMode: 'orthogonal' as const,
  globalTerraformConfig: {
    backend: { type: '', config: {} },
    provider: { region: 'us-east-1' },
    versionConstraints: {},
    environments: [],
    globalVariables: [],
  },
};

describe('ImportArchitectureDialog', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('passes JSON through the backend and applies canonical diagram state', async () => {
    vi.spyOn(apiClient, 'importArchitecture').mockResolvedValue({
      ok: true,
      data: {
        diagram: importedDiagram,
        imported_resource_count: 2,
        inferred_container_count: 1,
      },
    });
    const onClose = vi.fn();
    render(<ImportArchitectureDialog open onClose={onClose} />);

    fireEvent.change(screen.getByLabelText('Architecture JSON'), {
      target: { value: '{"project_name":"imported"}' },
    });
    fireEvent.click(screen.getByText('Import'));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(apiClient.importArchitecture).toHaveBeenCalledWith({ project_name: 'imported' });
    expect(useDiagramStore.getState().projectName).toBe('imported');
  });
});
