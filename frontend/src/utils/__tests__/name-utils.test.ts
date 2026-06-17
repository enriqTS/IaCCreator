import { describe, it, expect } from 'vitest';
import { generateDefaultName } from '@/utils/name-utils';
import type { CanvasObject, ArchitectureBlock, ServiceType } from '@/types/diagram';
import { DEFAULT_BLOCK_VISUAL, DEFAULT_LINE_VISUAL } from '@/types/diagram';

function makeBlock(id: string, serviceType: ServiceType, name: string): ArchitectureBlock {
  return {
    id,
    objectType: 'architecture-block',
    serviceType,
    name,
    position: { x: 0, y: 0 },
    config: {},
    terraformVariables: {},
    visualConfig: { ...DEFAULT_BLOCK_VISUAL },
    zIndex: 0,
  };
}

describe('generateDefaultName', () => {
  it('returns serviceType-1 for an empty canvas', () => {
    const objects = new Map<string, CanvasObject>();
    expect(generateDefaultName('lambda', objects)).toBe('lambda-1');
  });

  it('returns serviceType-1 when no blocks of the same type exist', () => {
    const objects = new Map<string, CanvasObject>();
    objects.set('1', makeBlock('1', 's3', 's3-1'));
    expect(generateDefaultName('lambda', objects)).toBe('lambda-1');
  });

  it('increments the counter based on existing blocks', () => {
    const objects = new Map<string, CanvasObject>();
    objects.set('1', makeBlock('1', 'lambda', 'lambda-1'));
    objects.set('2', makeBlock('2', 'lambda', 'lambda-2'));
    expect(generateDefaultName('lambda', objects)).toBe('lambda-3');
  });

  it('handles gaps from deletions (uses max, not count)', () => {
    const objects = new Map<string, CanvasObject>();
    objects.set('1', makeBlock('1', 'lambda', 'lambda-1'));
    objects.set('3', makeBlock('3', 'lambda', 'lambda-5'));
    // lambda-2, lambda-3, lambda-4 deleted; max is 5
    expect(generateDefaultName('lambda', objects)).toBe('lambda-6');
  });

  it('ignores non-pattern names (manually renamed blocks)', () => {
    const objects = new Map<string, CanvasObject>();
    objects.set('1', makeBlock('1', 'lambda', 'lambda-2'));
    objects.set('2', makeBlock('2', 'lambda', 'my-custom-lambda'));
    objects.set('3', makeBlock('3', 'lambda', 'production'));
    expect(generateDefaultName('lambda', objects)).toBe('lambda-3');
  });

  it('ignores non-architecture-block objects', () => {
    const objects = new Map<string, CanvasObject>();
    objects.set('1', {
      id: '1',
      objectType: 'line',
      name: 'lambda-5',
      start: { x: 0, y: 0 },
      end: { x: 100, y: 100 },
      sourceAnchor: null,
      targetAnchor: null,
      visualConfig: { ...DEFAULT_LINE_VISUAL },
      zIndex: 0,
    });
    expect(generateDefaultName('lambda', objects)).toBe('lambda-1');
  });

  it('ignores names with non-integer suffixes', () => {
    const objects = new Map<string, CanvasObject>();
    objects.set('1', makeBlock('1', 'lambda', 'lambda-abc'));
    objects.set('2', makeBlock('2', 'lambda', 'lambda-1.5'));
    objects.set('3', makeBlock('3', 'lambda', 'lambda-'));
    expect(generateDefaultName('lambda', objects)).toBe('lambda-1');
  });

  it('handles service types with hyphens correctly', () => {
    const objects = new Map<string, CanvasObject>();
    objects.set('1', makeBlock('1', 'api-gateway', 'api-gateway-1'));
    objects.set('2', makeBlock('2', 'api-gateway', 'api-gateway-3'));
    expect(generateDefaultName('api-gateway', objects)).toBe('api-gateway-4');
  });

  it('only considers blocks of the same service type for counter', () => {
    const objects = new Map<string, CanvasObject>();
    objects.set('1', makeBlock('1', 'lambda', 'lambda-10'));
    objects.set('2', makeBlock('2', 's3', 's3-5'));
    objects.set('3', makeBlock('3', 'dynamodb', 'dynamodb-3'));
    expect(generateDefaultName('s3', objects)).toBe('s3-6');
    expect(generateDefaultName('dynamodb', objects)).toBe('dynamodb-4');
    expect(generateDefaultName('lambda', objects)).toBe('lambda-11');
  });
});
