import fc from 'fast-check';
import { useDiagramStore } from '@/store/diagram-store';
import type { PickerItem } from '@/components/toolbar/ObjectPickerMenu';
import type { Tool } from '@/types/diagram';

// Feature: architecture-search-panel, Property 9: Click activates corresponding tool
// **Validates: Requirements 1.6**

/**
 * Arbitrary that generates a valid Tool value.
 */
const arbTool: fc.Arbitrary<Tool> = fc.oneof(
  fc.constant('pointer' as Tool),
  fc.constant('connector' as Tool),
  fc.constant('line' as Tool),
  fc.constant('text' as Tool),
  fc.record({
    type: fc.constant('place-service' as const),
    serviceType: fc.constantFrom('lambda', 's3', 'dynamodb', 'api-gateway', 'cloudwatch'),
  }),
  fc.record({
    type: fc.constant('place-shape' as const),
    shape: fc.constantFrom('rectangle', 'circle', 'ellipse', 'triangle', 'diamond', 'hexagon'),
  }),
  fc.record({
    type: fc.constant('place-uml' as const),
    umlKind: fc.constantFrom('class', 'interface', 'actor', 'use-case', 'component', 'package', 'node'),
  })
);

/**
 * Arbitrary that generates a PickerItem with a random tool.
 */
const arbPickerItem: fc.Arbitrary<PickerItem> = fc.record({
  name: fc.string({ minLength: 1, maxLength: 20 }),
  category: fc.constantFrom('Shapes', 'UML', 'Text', 'Lines & Arrows', 'AWS: Compute'),
  icon: fc.option(fc.constant('/icons/test.svg'), { nil: undefined }),
  tool: arbTool,
});

describe('Property 9: Click activates corresponding tool', () => {
  test('for any picker item, calling setActiveTool with item.tool sets activeTool to that value', () => {
    fc.assert(
      fc.property(arbPickerItem, (item) => {
        useDiagramStore.getState().setActiveTool(item.tool);
        const activeTool = useDiagramStore.getState().activeTool;
        expect(activeTool).toEqual(item.tool);
      }),
      { numRuns: 100 }
    );
  });
});
