import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import SemanticOutcomePanel from '@/components/config/overlay/SemanticOutcomePanel';
import { apiClient } from '@/utils/api-client';
import { useDiagramStore } from '@/store/diagram-store';
import { useEditorDomainStore } from '@/store/editor-domain-store';
import type { ArchitectureBlock, CanvasObject, SemanticContainerObject } from '@/types/diagram';

function region(): SemanticContainerObject {
  return {
    id: 'region', objectType: 'semantic-container', containerType: 'region', name: 'Primary Region',
    position: { x: 0, y: 0 }, config: { region: 'us-east-1' },
    visualConfig: { width: 400, height: 300, fillColor: '#000', borderColor: '#fff', borderWidth: 1 }, zIndex: 0,
  };
}

function subnet(): ArchitectureBlock {
  return {
    id: 'subnet', objectType: 'architecture-block', serviceType: 'subnet', name: 'Private Subnet',
    position: { x: 0, y: 0 }, config: {}, terraformVariables: {}, visualConfig: { width: 80, height: 80 },
    parentContainerId: 'region', zIndex: 1,
  };
}

describe('SemanticOutcomePanel', () => {
  beforeEach(() => {
    const objects = new Map<string, CanvasObject>([['region', region()], ['subnet', subnet()]]);
    useDiagramStore.setState({ canvasObjects: objects, connectors: new Map(), containmentInheritedValues: [], effectiveContainmentScopes: new Map() });
    useEditorDomainStore.setState({ containmentRules: [{ child_type: 'subnet', parent_type: 'region', outcome: 'inherited-scope' }] });
    vi.spyOn(apiClient, 'resolveContainment').mockResolvedValue({
      ok: true,
      data: {
        effective_scopes: [{ object_id: 'subnet', region: 'us-east-1' }],
        derived_connections: [],
        inherited_values: [{ object_id: 'subnet', field: 'availability_zone', value: 'us-east-1a', source_id: 'region', policy: 'managed' }],
        issues: [],
      },
    });
  });

  it('shows inherited sources, semantic outcome, and the Region limitation', async () => {
    render(<SemanticOutcomePanel objectId="subnet" />);

    expect(screen.getByTestId('containment-outcome').textContent).toContain('Scope inherited');
    await waitFor(() => expect(screen.getByText(/availability_zone/)).toBeDefined());
    expect(screen.getAllByText(/from Primary Region/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Multi-Region generation is not yet supported/)).toBeDefined();
  });
});
