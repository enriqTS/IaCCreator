import fc from 'fast-check';
import { getTabsForObject } from '@/components/config/SidebarPanel';
import type { LineObject, GeometricObject } from '@/types/diagram';

// Feature: sidebar-config-panel, Property 12: Non-architecture-block tab set
// **Validates: Requirements 8.5**
describe('Property 12: Non-architecture-block tab set', () => {
  const arbLineObject: fc.Arbitrary<LineObject> = fc.record({
    id: fc.string({ minLength: 1, maxLength: 20 }),
    objectType: fc.constant('line' as const),
    name: fc.string({ minLength: 0, maxLength: 30 }),
    start: fc.record({ x: fc.integer(), y: fc.integer() }),
    end: fc.record({ x: fc.integer(), y: fc.integer() }),
    sourceAnchor: fc.constant(null),
    targetAnchor: fc.constant(null),
    visualConfig: fc.record({
      color: fc.constant('#ffffff'),
      borderWidth: fc.integer({ min: 1, max: 10 }),
      strokeStyle: fc.constantFrom('solid' as const, 'dashed' as const),
      startArrow: fc.boolean(),
      endArrow: fc.boolean(),
    }),
    zIndex: fc.integer({ min: 0, max: 1000 }),
    groupId: fc.option(fc.string({ minLength: 1, maxLength: 20 }), { nil: undefined }),
  });

  const arbGeometricObject: fc.Arbitrary<GeometricObject> = fc.record({
    id: fc.string({ minLength: 1, maxLength: 20 }),
    objectType: fc.constant('geometric' as const),
    name: fc.string({ minLength: 0, maxLength: 30 }),
    position: fc.record({ x: fc.integer(), y: fc.integer() }),
    visualConfig: fc.record({
      width: fc.integer({ min: 40, max: 400 }),
      height: fc.integer({ min: 40, max: 400 }),
      fill: fc.boolean(),
      fillColor: fc.constant('#3b82f6'),
      borderColor: fc.constant('#ffffff'),
      borderWidth: fc.integer({ min: 1, max: 10 }),
      shape: fc.constantFrom('rectangle' as const, 'ellipse' as const),
    }),
    zIndex: fc.integer({ min: 0, max: 1000 }),
    groupId: fc.option(fc.string({ minLength: 1, maxLength: 20 }), { nil: undefined }),
  });

  test('getTabsForObject returns ["Connection", "Visual"] for any line object', () => {
    fc.assert(
      fc.property(arbLineObject, (line) => {
        const tabs = getTabsForObject(line);
        expect(tabs).toEqual(['Connection', 'Visual']);
      }),
      { numRuns: 100 },
    );
  });

  test('getTabsForObject returns ["Visual"] for any geometric object', () => {
    fc.assert(
      fc.property(arbGeometricObject, (geo) => {
        const tabs = getTabsForObject(geo);
        expect(tabs).toEqual(['Visual']);
      }),
      { numRuns: 100 },
    );
  });
});
