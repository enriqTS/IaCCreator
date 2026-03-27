import fc from 'fast-check';
import { getTabsForObject } from '@/components/config/SidebarPanel';
import type { ArchitectureBlock, ServiceType } from '@/types/diagram';

// Feature: sidebar-config-panel, Property 11: Architecture block tab set
// **Validates: Requirements 8.4**
describe('Property 11: Architecture block tab set', () => {
  const serviceTypes: ServiceType[] = [
    'lambda',
    's3',
    'dynamodb',
    'api-gateway',
    'cloudwatch',
    'iam',
  ];

  const arbServiceType = fc.constantFrom(...serviceTypes);

  const arbArchitectureBlock: fc.Arbitrary<ArchitectureBlock> = fc.record({
    id: fc.string({ minLength: 1, maxLength: 20 }),
    objectType: fc.constant('architecture-block' as const),
    serviceType: arbServiceType,
    name: fc.string({ minLength: 0, maxLength: 30 }),
    position: fc.record({ x: fc.integer(), y: fc.integer() }),
    config: fc.constant({}),
    terraformVariables: fc.constant({}),
    visualConfig: fc.record({
      width: fc.integer({ min: 40, max: 400 }),
      height: fc.integer({ min: 40, max: 400 }),
    }),
    zIndex: fc.integer({ min: 0, max: 1000 }),
    groupId: fc.option(fc.string({ minLength: 1, maxLength: 20 }), { nil: undefined }),
  });

  test('getTabsForObject returns ["Variables", "Visual"] for any architecture block', () => {
    fc.assert(
      fc.property(arbArchitectureBlock, (block) => {
        const tabs = getTabsForObject(block);
        expect(tabs).toEqual(['Variables', 'Visual']);
      }),
      { numRuns: 100 },
    );
  });
});
