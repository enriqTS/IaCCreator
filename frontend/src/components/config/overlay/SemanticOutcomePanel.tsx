'use client';

import { useEffect } from 'react';
import { Info, LockKeyhole } from 'lucide-react';
import { useDiagramStore } from '@/store/diagram-store';
import { useEditorDomainStore } from '@/store/editor-domain-store';
import { semanticType } from '@/utils/semantic-containment';
import ConnectionContributionPreview from './ConnectionContributionPreview';

export default function SemanticOutcomePanel({ objectId }: { objectId: string }) {
  const object = useDiagramStore((state) => state.canvasObjects.get(objectId));
  const objects = useDiagramStore((state) => state.canvasObjects);
  const connectors = useDiagramStore((state) => state.connectors);
  const defaultScope = useDiagramStore((state) => state.effectiveContainmentScopes.get(objectId));
  const environmentScopes = useDiagramStore((state) => state.environmentContainmentScopes);
  const environments = useDiagramStore((state) => state.environments);
  const activeEnvironment = useDiagramStore((state) => state.activeEnvironmentName);
  const setActiveEnvironment = useDiagramStore((state) => state.setActiveEnvironment);
  const scope = activeEnvironment
    ? environmentScopes.get(activeEnvironment)?.get(objectId) ?? defaultScope
    : defaultScope;
  const inheritedValues = useDiagramStore((state) => state.containmentInheritedValues);
  const inherited = inheritedValues.filter((value) => value.object_id === objectId);
  const refresh = useDiagramStore((state) => state.refreshContainmentResolution);
  const rules = useEditorDomainStore((state) => state.containmentRules);

  useEffect(() => {
    void refresh();
  }, [objectId, refresh]);

  if (!object) return null;
  const parent = 'parentContainerId' in object && object.parentContainerId
    ? objects.get(object.parentContainerId)
    : undefined;
  const rule = parent
    ? rules.find((candidate) => candidate.child_type === semanticType(object)
      && candidate.parent_type === semanticType(parent))
    : undefined;
  const managedConnectors = [...connectors.values()].filter((connector) =>
    connector.origin === 'containment'
      && (connector.sourceId === objectId || connector.targetId === objectId));
  const scopeValues = [
    ['Region', scope?.region],
    ['Availability Zone', scope?.availability_zone],
    ['VPC', scope?.vpc_id ? objects.get(scope.vpc_id)?.name ?? scope.vpc_id : null],
    ['Subnet', scope?.subnet_id ? objects.get(scope.subnet_id)?.name ?? scope.subnet_id : null],
  ].filter((entry): entry is [string, string] => typeof entry[1] === 'string' && entry[1].length > 0);

  return (
    <div data-testid="semantic-outcome-panel" className="flex flex-col gap-4 py-2">
      <div className="rounded-md border bg-muted/30 px-3 py-2">
        <div className="text-xs font-semibold">Containment outcome</div>
        <div data-testid="containment-outcome" className="mt-1 text-xs text-muted-foreground">
          {!parent
            ? 'Not currently contained.'
            : rule?.outcome === 'terraform-connection'
              ? `Terraform connection managed by ${parent.name}.`
              : rule?.outcome === 'inherited-scope'
                ? `Scope inherited from ${parent.name}.`
                : `Visual-only membership in ${parent.name}.`}
        </div>
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between gap-3">
          <h3 className="text-xs font-semibold text-muted-foreground">Effective scope</h3>
          {environments.length > 0 && (
            <select
              aria-label="Scope environment"
              className="h-7 rounded-md border bg-background px-2 text-xs"
              value={activeEnvironment ?? ''}
              onChange={(event) => setActiveEnvironment(event.target.value || null)}
            >
              <option value="">Project default</option>
              {environments.map((environment) => (
                <option key={environment.name} value={environment.name}>{environment.name}</option>
              ))}
            </select>
          )}
        </div>
        {scopeValues.length > 0 ? (
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
            {scopeValues.map(([label, value]) => (
              <div key={label} className="contents">
                <dt className="text-muted-foreground">{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        ) : <span className="text-xs text-muted-foreground">No inherited scope.</span>}
      </div>

      {inherited.length > 0 && (
        <div>
          <h3 className="mb-2 text-xs font-semibold text-muted-foreground">Managed fields</h3>
          <ul className="flex flex-col gap-1">
            {inherited.map((value) => (
              <li key={value.field} className="flex items-center gap-2 rounded border px-2 py-1 text-xs">
                <LockKeyhole className="size-3 text-muted-foreground" />
                <span className="font-mono">{value.field}</span>
                <span className="ml-auto text-muted-foreground">
                  {String(value.value)} from {objects.get(value.source_id)?.name ?? value.source_id}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {managedConnectors.map((connector) => (
        <div key={connector.id}>
          <h3 className="mb-2 text-xs font-semibold text-muted-foreground">Derived connection</h3>
          <ConnectionContributionPreview connectorId={connector.id} />
        </div>
      ))}

      <div className="flex gap-2 rounded-md border border-blue-500/30 bg-blue-500/10 px-3 py-2 text-xs">
        <Info className="mt-0.5 size-3 shrink-0" />
        Region containers must match the project provider Region. Multi-Region generation is not yet supported.
      </div>
    </div>
  );
}
