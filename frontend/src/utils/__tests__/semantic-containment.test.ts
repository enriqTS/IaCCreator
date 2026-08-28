import { describe, expect, it } from 'vitest';
import type { ArchitectureBlock, CanvasObject, SemanticContainerObject } from '@/types/diagram';
import { findContainmentDropCandidate, hiddenByCollapsedAncestor, normalizeSemanticZOrder, overlapRatio } from '@/utils/semantic-containment';

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

describe('semantic containment geometry', () => {
  it('selects the deepest overlapping target and reports catalog validity', () => {
    const region = { ...container('region', 0), containerType: 'region' as const, visualConfig: { ...container('region', 0).visualConfig, width: 500, height: 500 } };
    const subnet = {
      ...resource('subnet', 1, 'region'),
      serviceType: 'subnet' as const,
      presentation: 'container' as const,
      visualConfig: { width: 300, height: 300 },
    };
    const workload = { ...resource('workload', 2, ''), serviceType: 'lambda' as const };
    const objects = new Map<string, CanvasObject>([
      [region.id, region],
      [subnet.id, subnet],
      [workload.id, workload],
    ]);

    const candidate = findContainmentDropCandidate('workload', objects, [
      { child_type: 'lambda', parent_type: 'subnet' },
    ]);

    expect(candidate).toEqual({ id: 'subnet', valid: true, depth: 1 });
  });

  it('hides every nested descendant of a collapsed boundary', () => {
    const region = { ...container('region', 0), collapsed: true };
    const subnet = container('subnet', 1, 'region');
    const workload = resource('workload', 2, 'subnet');
    const objects = new Map<string, CanvasObject>([
      [region.id, region],
      [subnet.id, subnet],
      [workload.id, workload],
    ]);

    expect(hiddenByCollapsedAncestor(region, objects)).toBe(false);
    expect(hiddenByCollapsedAncestor(subnet, objects)).toBe(true);
    expect(hiddenByCollapsedAncestor(workload, objects)).toBe(true);
  });

  it('uses the dragged object area as the overlap denominator', () => {
    expect(overlapRatio(
      { x: 0, y: 0, width: 100, height: 100 },
      { x: 50, y: 0, width: 100, height: 100 },
    )).toBe(0.5);
  });
});

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
