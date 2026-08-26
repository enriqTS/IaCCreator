/** Backend-owned service support metadata used by the local icon renderer. */

import { create } from 'zustand';
import { apiClient } from '@/utils/api-client';
import { useDiagramStore } from '@/store/diagram-store';
import { hydrateSchemas } from '@/store/schema-store';
import { hydrateConnectionSchemas } from '@/connections/schema-store';
import { hydrateNamingRules } from '@/store/naming-store';

interface EditorDomainState {
  supportedServices: Set<string> | null;
  load: () => Promise<void>;
}

export const useEditorDomainStore = create<EditorDomainState>()((set) => ({
  supportedServices: null,
  load: async () => {
    const result = await apiClient.getEditorBootstrap();
    if (!result.ok) return;
    hydrateSchemas(result.data.variable_schemas);
    hydrateConnectionSchemas(result.data.connection_schemas);
    hydrateNamingRules(result.data.naming_rules);
    set({
      supportedServices: new Set(
        result.data.services
          .filter((service) => service.supported)
          .map((service) => service.service_type),
      ),
    });
    const diagram = useDiagramStore.getState();
    if (
      diagram.currentDiagramId === null
      && diagram.globalTerraformConfig.backend.type === ''
      && diagram.globalTerraformConfig.provider.region === ''
    ) {
      useDiagramStore.setState({
        globalTerraformConfig: structuredClone(result.data.global_terraform_defaults),
      });
    }
  },
}));
