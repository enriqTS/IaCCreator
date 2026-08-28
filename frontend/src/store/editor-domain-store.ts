/** Backend-owned service support metadata used by the local icon renderer. */

import { create } from 'zustand';
import { apiClient } from '@/utils/api-client';
import { useDiagramStore } from '@/store/diagram-store';
import { hydrateSchemas } from '@/store/schema-store';
import { hydrateConnectionSchemas } from '@/connections/schema-store';
import { hydrateNamingRules } from '@/store/naming-store';

export interface ServiceCapabilities {
  diagram: boolean;
  terraform: boolean;
  configurable: boolean;
  connectable: boolean;
}

export interface SemanticContainerDefinition {
  container_type: string;
  display_name: string;
  allowed_parent_types: string[];
  allowed_child_types: string[];
  config_fields: string[];
}

export interface ContainmentRule {
  child_type: string;
  parent_type: string;
  connection_type?: string | null;
  outcome: 'terraform-connection' | 'inherited-scope' | 'visual-only';
}

interface EditorDomainState {
  serviceCapabilities: Map<string, ServiceCapabilities> | null;
  semanticContainerTypes: Set<string> | null;
  semanticContainerDefinitions: SemanticContainerDefinition[];
  containmentRules: ContainmentRule[];
  load: () => Promise<void>;
}

export const useEditorDomainStore = create<EditorDomainState>()((set) => ({
  serviceCapabilities: null,
  semanticContainerTypes: null,
  semanticContainerDefinitions: [],
  containmentRules: [],
  load: async () => {
    const result = await apiClient.getEditorBootstrap();
    if (!result.ok) return;
    hydrateSchemas(result.data.variable_schemas);
    hydrateConnectionSchemas(result.data.connection_schemas);
    hydrateNamingRules(result.data.naming_rules);
    set({
      serviceCapabilities: new Map(
        result.data.services.map((service) => [service.service_type, service.capabilities]),
      ),
      semanticContainerTypes: new Set(
        result.data.containment?.container_types.map((container) => container.container_type) ?? [],
      ),
      semanticContainerDefinitions: result.data.containment?.container_types ?? [],
      containmentRules: result.data.containment?.rules.map((rule) => ({
        child_type: rule.child_type,
        parent_type: rule.parent_type,
        connection_type: rule.connection_type,
        outcome: rule.outcome,
      })) ?? [],
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
