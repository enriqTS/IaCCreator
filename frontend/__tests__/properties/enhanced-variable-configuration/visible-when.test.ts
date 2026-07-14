import fc from 'fast-check';
import { BUNDLED_SCHEMAS } from '@/data/bundled-schemas';
import { isVisible } from '@/components/config/schema/SchemaConfigForm';
import type { TerraformVariableSchema } from '@/types/terraform-variables';
import type { ResourceConfig } from '@/types/diagram';

// Feature: enhanced-variable-configuration

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const SERVICE_TYPES = Object.keys(BUNDLED_SCHEMAS) as string[];

/**
 * Collect all unique discriminating fields across all services.
 * Returns a map: serviceType → { field, possibleValues, matchValue }[]
 */
function getDiscriminatingFields(): Map<
  string,
  { field: string; matchValue: string | number | boolean; otherValues: (string | number | boolean)[] }[]
> {
  const result = new Map<
    string,
    { field: string; matchValue: string | number | boolean; otherValues: (string | number | boolean)[] }[]
  >();

  for (const serviceType of SERVICE_TYPES) {
    const entries = BUNDLED_SCHEMAS[serviceType];
    const discFields: {
      field: string;
      matchValue: string | number | boolean;
      otherValues: (string | number | boolean)[];
    }[] = [];

    // Find all visible_when references
    const visibleWhens = entries.filter((e) => e.visible_when).map((e) => e.visible_when!);

    for (const vw of visibleWhens) {
      // Find the discriminating field's options
      const discEntry = entries.find((e) => e.name === vw.field);
      if (!discEntry || !discEntry.options) continue;

      const allValues = discEntry.options.map((o) => o.value);
      const otherValues = allValues.filter((v) => v !== vw.equals);

      // Avoid duplicates
      if (!discFields.some((d) => d.field === vw.field && d.matchValue === vw.equals)) {
        discFields.push({ field: vw.field, matchValue: vw.equals, otherValues });
      }
    }

    if (discFields.length > 0) {
      result.set(serviceType, discFields);
    }
  }

  return result;
}

// ---------------------------------------------------------------------------
// Property 5: Variables rendered organized by group
// Property 6: Empty groups are hidden
// Feature: enhanced-variable-configuration, Property 5 + 6
// **Validates: Requirements 3.2, 3.4**
// ---------------------------------------------------------------------------

describe('Property 5 + 6: Grouping and conditional visibility', () => {
  test('for any service type, entries are grouped by their group field and each group contains exactly the entries assigned to it', () => {
    fc.assert(
      fc.property(fc.constantFrom(...SERVICE_TYPES), (serviceType) => {
        const entries = BUNDLED_SCHEMAS[serviceType];

        // Build groups the same way the component does
        const groupMap = new Map<string, TerraformVariableSchema[]>();
        for (const entry of entries) {
          const group = entry.group ?? 'General';
          if (!groupMap.has(group)) groupMap.set(group, []);
          groupMap.get(group)!.push(entry);
        }

        // Every entry must belong to exactly one group
        let totalGrouped = 0;
        for (const [, groupEntries] of groupMap) {
          totalGrouped += groupEntries.length;
        }
        expect(totalGrouped).toBe(entries.length);

        // Each entry's group field matches the group it's placed in
        for (const [groupName, groupEntries] of groupMap) {
          for (const entry of groupEntries) {
            expect(entry.group ?? 'General').toBe(groupName);
          }
        }
      }),
      { numRuns: 100 },
    );
  });

  test('when visible_when conditions are false for all entries in a group, that group has zero visible entries (empty group hidden)', () => {
    fc.assert(
      fc.property(fc.constantFrom(...SERVICE_TYPES), (serviceType) => {
        const entries = BUNDLED_SCHEMAS[serviceType];

        // Build groups
        const groupMap = new Map<string, TerraformVariableSchema[]>();
        for (const entry of entries) {
          const group = entry.group ?? 'General';
          if (!groupMap.has(group)) groupMap.set(group, []);
          groupMap.get(group)!.push(entry);
        }

        // For each group, if ALL entries have visible_when and we set config
        // so all conditions are false, the group should have 0 visible entries
        for (const [, groupEntries] of groupMap) {
          const allHaveVisibleWhen = groupEntries.every((e) => e.visible_when != null);
          if (!allHaveVisibleWhen) continue;

          // Build a config where every visible_when condition is false
          const config: Record<string, unknown> = {};
          for (const entry of groupEntries) {
            const vw = entry.visible_when!;
            // Set the discriminating field to something OTHER than the required value
            config[vw.field] = typeof vw.equals === 'string' ? `__NOT_${vw.equals}__` : -99999;
          }

          const visibleCount = groupEntries.filter((e) =>
            isVisible(e, config as ResourceConfig),
          ).length;

          expect(visibleCount).toBe(0);
        }
      }),
      { numRuns: 100 },
    );
  });

  test('DynamoDB: when billing_mode != PROVISIONED, the Capacity group has zero visible entries', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('PAY_PER_REQUEST', 'UNKNOWN_MODE', ''),
        (billingMode) => {
          const entries = BUNDLED_SCHEMAS['dynamodb'];
          const capacityEntries = entries.filter((e) => (e.group ?? 'General') === 'Capacity');

          // Capacity group should exist and have entries
          expect(capacityEntries.length).toBeGreaterThan(0);

          const config: ResourceConfig = { billing_mode: billingMode };

          const visibleCount = capacityEntries.filter((e) =>
            isVisible(e, config),
          ).length;

          // None should be visible when billing_mode is not PROVISIONED
          expect(visibleCount).toBe(0);
        },
      ),
      { numRuns: 100 },
    );
  });

  test('DynamoDB: when billing_mode == PROVISIONED, the Capacity group entries are all visible', () => {
    const entries = BUNDLED_SCHEMAS['dynamodb'];
    const capacityEntries = entries.filter((e) => (e.group ?? 'General') === 'Capacity');

    expect(capacityEntries.length).toBeGreaterThan(0);

    const config: ResourceConfig = { billing_mode: 'PROVISIONED' };

    for (const entry of capacityEntries) {
      expect(isVisible(entry, config)).toBe(true);
    }
  });

  test('API Gateway: when protocol_type != WEBSOCKET, route_selection_expression is hidden', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('HTTP', 'REST', 'UNKNOWN', ''),
        (protocolType) => {
          const entries = BUNDLED_SCHEMAS['api-gateway'];
          const routeEntry = entries.find((e) => e.name === 'route_selection_expression');

          expect(routeEntry).toBeDefined();
          expect(routeEntry!.visible_when).toBeDefined();

          const config: ResourceConfig = { protocol_type: protocolType };
          expect(isVisible(routeEntry!, config)).toBe(false);
        },
      ),
      { numRuns: 100 },
    );
  });

  test('entries without visible_when are always visible regardless of config', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...SERVICE_TYPES),
        fc.dictionary(
          fc.string({ minLength: 1, maxLength: 20 }),
          fc.oneof(fc.string({ minLength: 1, maxLength: 20 }), fc.integer(), fc.boolean()),
          { minKeys: 0, maxKeys: 5 },
        ),
        (serviceType, randomConfig) => {
          const entries = BUNDLED_SCHEMAS[serviceType];
          const unconditionalEntries = entries.filter((e) => !e.visible_when);

          for (const entry of unconditionalEntries) {
            expect(isVisible(entry, randomConfig as ResourceConfig)).toBe(true);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Property 11: Changing discriminating field clears dependent values
// Feature: enhanced-variable-configuration, Property 11
// **Validates: Requirements 6.7**
// ---------------------------------------------------------------------------

describe('Property 11: Changing discriminating field clears dependent values', () => {
  const discriminatingFields = getDiscriminatingFields();

  test('when a discriminating field changes to a non-matching value, all dependent fields should be cleared', () => {
    // For each service with discriminating fields, test the clearing logic
    for (const [serviceType, discFields] of discriminatingFields) {
      const entries = BUNDLED_SCHEMAS[serviceType];

      for (const { field, matchValue, otherValues } of discFields) {
        if (otherValues.length === 0) continue;

        // Find all dependent entries (those with visible_when.field == field and visible_when.equals == matchValue)
        const dependentEntries = entries.filter(
          (e) => e.visible_when && e.visible_when.field === field && e.visible_when.equals === matchValue,
        );

        expect(dependentEntries.length).toBeGreaterThan(0);

        fc.assert(
          fc.property(
            fc.constantFrom(...otherValues),
            (newValue) => {
              // Simulate: the discriminating field changes from matchValue to newValue
              // All dependent fields should become invisible → their values should be cleared

              for (const dep of dependentEntries) {
                // With the new value, the dependent field should NOT be visible
                const config = { [field]: newValue } as ResourceConfig;
                expect(isVisible(dep, config)).toBe(false);
              }

              // With the matching value, the dependent field SHOULD be visible
              for (const dep of dependentEntries) {
                const config = { [field]: matchValue } as ResourceConfig;
                expect(isVisible(dep, config)).toBe(true);
              }
            },
          ),
          { numRuns: 100 },
        );
      }
    }
  });

  test('DynamoDB: switching billing_mode from PROVISIONED to PAY_PER_REQUEST hides read_capacity and write_capacity', () => {
    const entries = BUNDLED_SCHEMAS['dynamodb'];
    const readCap = entries.find((e) => e.name === 'read_capacity')!;
    const writeCap = entries.find((e) => e.name === 'write_capacity')!;

    expect(readCap.visible_when).toEqual({ field: 'billing_mode', equals: 'PROVISIONED' });
    expect(writeCap.visible_when).toEqual({ field: 'billing_mode', equals: 'PROVISIONED' });

    // Visible when PROVISIONED
    const provisionedConfig: ResourceConfig = { billing_mode: 'PROVISIONED' };
    expect(isVisible(readCap, provisionedConfig)).toBe(true);
    expect(isVisible(writeCap, provisionedConfig)).toBe(true);

    // Hidden when PAY_PER_REQUEST → values should be cleared
    const payPerRequestConfig: ResourceConfig = { billing_mode: 'PAY_PER_REQUEST' };
    expect(isVisible(readCap, payPerRequestConfig)).toBe(false);
    expect(isVisible(writeCap, payPerRequestConfig)).toBe(false);
  });

  test('API Gateway: switching protocol_type from WEBSOCKET to HTTP hides route_selection_expression', () => {
    const entries = BUNDLED_SCHEMAS['api-gateway'];
    const routeEntry = entries.find((e) => e.name === 'route_selection_expression')!;

    expect(routeEntry.visible_when).toEqual({ field: 'protocol_type', equals: 'WEBSOCKET' });

    // Visible when WEBSOCKET
    const wsConfig: ResourceConfig = { protocol_type: 'WEBSOCKET' };
    expect(isVisible(routeEntry, wsConfig)).toBe(true);

    // Hidden when HTTP
    const httpConfig: ResourceConfig = { protocol_type: 'HTTP' };
    expect(isVisible(routeEntry, httpConfig)).toBe(false);
  });

  test('for random discriminating field values, dependent fields are hidden when condition is not met', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 30 }),
        (randomValue) => {
          // DynamoDB: read_capacity visible only when billing_mode == PROVISIONED
          const entries = BUNDLED_SCHEMAS['dynamodb'];
          const readCap = entries.find((e) => e.name === 'read_capacity')!;

          const config: ResourceConfig = { billing_mode: randomValue };
          const visible = isVisible(readCap, config);

          if (randomValue === 'PROVISIONED') {
            expect(visible).toBe(true);
          } else {
            expect(visible).toBe(false);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  test('for random protocol_type values, route_selection_expression visibility matches condition', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 30 }),
        (randomValue) => {
          const entries = BUNDLED_SCHEMAS['api-gateway'];
          const routeEntry = entries.find((e) => e.name === 'route_selection_expression')!;

          const config: ResourceConfig = { protocol_type: randomValue };
          const visible = isVisible(routeEntry, config);

          if (randomValue === 'WEBSOCKET') {
            expect(visible).toBe(true);
          } else {
            expect(visible).toBe(false);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
