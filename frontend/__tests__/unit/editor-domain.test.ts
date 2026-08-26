import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useDiagramStore } from '@/store/diagram-store';
import { useEditorDomainStore } from '@/store/editor-domain-store';
import { apiClient } from '@/utils/api-client';
import { getSchemas } from '@/store/schema-store';
import { validateResourceName } from '@/store/naming-store';

const globalDefaults = {
  backend: { type: 'local', config: {} },
  provider: { region: 'eu-west-1' },
  versionConstraints: {},
  environments: [],
  globalVariables: [],
};

describe('backend-owned editor domain', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useDiagramStore.setState({
      canvasObjects: new Map(),
      connectors: new Map(),
      currentDiagramId: null,
      globalTerraformConfig: {
        backend: { type: '', config: {} },
        provider: { region: '' },
        versionConstraints: {},
        environments: [],
        globalVariables: [],
      },
    });
    useEditorDomainStore.setState({ supportedServices: null });
  });

  it('hydrates support, schemas, naming, and global defaults from bootstrap', async () => {
    vi.spyOn(apiClient, 'getEditorBootstrap').mockResolvedValue({
      ok: true,
      data: {
        services: [
          { service_type: 'lambda', display_name: 'Lambda', category: 'AWS', supported: true },
          { service_type: 'clean-rooms', display_name: 'Clean Rooms', category: 'AWS', supported: false },
        ],
        variable_schemas: { lambda: [] },
        connection_schemas: [],
        naming_rules: { pattern: '^[a-z]+$', description: 'lowercase only', max_length: 20 },
        global_terraform_defaults: globalDefaults,
        diagram_version: 3,
      },
    });

    await useEditorDomainStore.getState().load();

    expect(useEditorDomainStore.getState().supportedServices).toEqual(new Set(['lambda']));
    expect(getSchemas()).toEqual({ lambda: [] });
    expect(validateResourceName('INVALID')).toBe('lowercase only');
    expect(useDiagramStore.getState().globalTerraformConfig.provider.region).toBe('eu-west-1');
  });

  it('patches a placed resource with initialization returned by the backend', async () => {
    vi.spyOn(apiClient, 'initializeResource').mockResolvedValue({
      ok: true,
      data: {
        name: 'lambda-1',
        config: { runtime: 'python3.14' },
        terraform_variables: { memory_size: 128 },
      },
    });

    const id = useDiagramStore.getState().addCanvasObject({
      objectType: 'architecture-block',
      serviceType: 'lambda',
      name: '',
      position: { x: 0, y: 0 },
      config: {},
      terraformVariables: {},
      visualConfig: { width: 80, height: 80 },
    });
    await vi.waitFor(() => {
      const block = useDiagramStore.getState().canvasObjects.get(id);
      expect(block?.name).toBe('lambda-1');
    });

    const block = useDiagramStore.getState().canvasObjects.get(id);
    expect(block?.objectType === 'architecture-block' && block.config.runtime).toBe('python3.14');
  });
});
