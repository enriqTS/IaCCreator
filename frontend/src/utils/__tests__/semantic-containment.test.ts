import { describe, expect, it } from 'vitest';
import type { ArchitectureBlock, CanvasObject, SemanticContainerObject } from '@/types/diagram';
import { normalizeSemanticZOrder } from '@/utils/semantic-containment';

function container(id: string, zIndex: number, parentContainerId?: string): SemanticContainerObject {
  return {
    id,
    objectType: 'semantic-container',
    containerType: 'generic',
    name: id,
    position: { x: 0, y: 0 },
    config: {},
    visualConfig: { width: 100, height: 100, fillColor: '#000', borderColor: '#fff', borderWidth: 1 },
    zIndex,
    parentContainerId,
  };
}

function resource(id: string, zIndex: number, parentContainerId: string): ArchitectureBlock {
  return {
    id,
    objectType: 'architecture-block',
    serviceType: 'ec2',
    name: id,
    position: { x: 0, y: 0 },
    config: {},
    terraformVariables: {},
    visualConfig: { width: 80, height: 80 },
    zIndex,
    parentContainerId,
  };
}

describe('normalizeSemanticZOrder', () => {
  it('places every semantic parent below all descendants', () => {
    const objects = new Map<string, CanvasObject>([
      ['workload', resource('workload', 0, 'az')],
      ['az', container('az', 8, 'region')],
      ['region', container('region', 9)],
    ]);

    const normalized = normalizeSemanticZOrder(objects);

    expect(normalized.get('region')!.zIndex).toBeLessThan(normalized.get('az')!.zIndex);
    expect(normalized.get('az')!.zIndex).toBeLessThan(normalized.get('workload')!.zIndex);
  });
});
