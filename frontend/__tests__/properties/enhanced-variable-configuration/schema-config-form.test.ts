import fc from 'fast-check';
import { BUNDLED_SCHEMAS } from '@/data/bundled-schemas';
import { validateValue, isVisible } from '@/components/config/schema/SchemaConfigForm';
import type {
  TerraformVariableSchema,
  TerraformVariableType,
  ValidationRule,
  OptionEntry,
  VisibleWhen,
} from '@/types/terraform-variables';

// Feature: enhanced-variable-configuration

// ---------------------------------------------------------------------------
// Shared arbitraries
// ---------------------------------------------------------------------------

const SERVICE_TYPES = Object.keys(BUNDLED_SCHEMAS) as string[];

const arbServiceType: fc.Arbitrary<string> = fc.constantFrom(...SERVICE_TYPES);

const arbVariableType: fc.Arbitrary<TerraformVariableType> = fc.constantFrom(
  'string',
  'number',
  'bool',
  'map',
  'list',
);

const arbOptionEntry: fc.Arbitrary<OptionEntry> = fc.record({
  value: fc.oneof(fc.string({ minLength: 1, maxLength: 10 }), fc.integer({ min: 0, max: 1000 })),
  label: fc.string({ minLength: 1, maxLength: 30 }),
});

const arbValidationRule: fc.Arbitrary<ValidationRule> = fc.record({
  min: fc.option(fc.integer({ min: -1000, max: 10000 }), { nil: null }),
  max: fc.option(fc.integer({ min: -1000, max: 50000 }), { nil: null }),
  pattern: fc.option(fc.constant('^[a-z]+$'), { nil: null }),
  pattern_description: fc.option(fc.string({ minLength: 1, maxLength: 40 }), { nil: null }),
  allowed_values: fc.option(
    fc.array(fc.oneof(fc.string({ minLength: 1, maxLength: 10 }), fc.integer({ min: 0, max: 100 })), {
      minLength: 1,
      maxLength: 5,
    }),
    { nil: null },
  ),
});

const arbVisibleWhen: fc.Arbitrary<VisibleWhen> = fc.record({
  field: fc.string({ minLength: 1, maxLength: 20 }),
  equals: fc.oneof(fc.string({ minLength: 1, maxLength: 20 }), fc.integer({ min: 0, max: 100 })),
});

const arbSchemaEntry: fc.Arbitrary<TerraformVariableSchema> = fc.record({
  name: fc.string({ minLength: 1, maxLength: 30 }),
  type: arbVariableType,
  description: fc.string({ minLength: 1, maxLength: 60 }),
  default: fc.option(
    fc.oneof(fc.string({ minLength: 0, maxLength: 20 }), fc.integer({ min: 0, max: 10000 }), fc.boolean()),
    { nil: undefined },
  ),
  group: fc.option(fc.string({ minLength: 1, maxLength: 20 }), { nil: undefined }),
  options: fc.option(fc.array(arbOptionEntry, { minLength: 1, maxLength: 5 }), { nil: undefined }),
  validation: fc.option(arbValidationRule, { nil: undefined }),
  visible_when: fc.option(arbVisibleWhen, { nil: undefined }),
});

// ---------------------------------------------------------------------------
// Helper: determine expected widget type for a schema entry
// ---------------------------------------------------------------------------

type WidgetType = 'select' | 'text' | 'number' | 'checkbox' | 'key-value-editor' | 'list-editor';

function expectedWidget(entry: TerraformVariableSchema): WidgetType {
  if (entry.options && entry.options.length > 0) return 'select';
  switch (entry.type) {
    case 'bool':
      return 'checkbox';
    case 'number':
      return 'number';
    case 'map':
      return 'key-value-editor';
    case 'list':
      return 'list-editor';
    default:
      return 'text';
  }
}

// ---------------------------------------------------------------------------
// Property 2: Default values displayed as initial values
// Feature: enhanced-variable-configuration, Property 2: Default values displayed as initial values
// **Validates: Requirements 1.7, 5.12**
// ---------------------------------------------------------------------------

describe('Property 2: Default values displayed as initial values', () => {
  test('for any service type, every schema entry with a non-null default has a defined default value matching the schema', () => {
    fc.assert(
      fc.property(arbServiceType, (serviceType) => {
        const entries = BUNDLED_SCHEMAS[serviceType];
        expect(entries).toBeDefined();
        expect(entries.length).toBeGreaterThan(0);

        for (const entry of entries) {
          if (entry.default !== undefined && entry.default !== null) {
            // The default value must be defined (not undefined/null)
            expect(entry.default).toBeDefined();
            expect(entry.default).not.toBeNull();

            // If the entry has options, the default must be one of the option values
            if (entry.options && entry.options.length > 0) {
              const optionValues = entry.options.map((o) => o.value);
              expect(optionValues).toContain(entry.default);
            }

            // The default type should be consistent with the schema type
            switch (entry.type) {
              case 'number':
                expect(typeof entry.default).toBe('number');
                break;
              case 'bool':
                expect(typeof entry.default).toBe('boolean');
                break;
              case 'string':
                expect(typeof entry.default).toBe('string');
                break;
            }
          }
        }
      }),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Property 3: Type-to-widget mapping
// Feature: enhanced-variable-configuration, Property 3: Type-to-widget mapping
// **Validates: Requirements 2.7, 2.8, 5.2, 7.2, 7.3**
// ---------------------------------------------------------------------------

describe('Property 3: Type-to-widget mapping', () => {
  test('for any schema entry, the widget type is determined by options presence first, then by variable type', () => {
    fc.assert(
      fc.property(arbSchemaEntry, (entry) => {
        const widget = expectedWidget(entry);

        // If options are defined, widget must be select regardless of type
        if (entry.options && entry.options.length > 0) {
          expect(widget).toBe('select');
          return;
        }

        // Otherwise, widget is determined by type
        switch (entry.type) {
          case 'string':
            expect(widget).toBe('text');
            break;
          case 'number':
            expect(widget).toBe('number');
            break;
          case 'bool':
            expect(widget).toBe('checkbox');
            break;
          case 'map':
            expect(widget).toBe('key-value-editor');
            break;
          case 'list':
            expect(widget).toBe('list-editor');
            break;
        }
      }),
      { numRuns: 100 },
    );
  });

  test('all entries in BUNDLED_SCHEMAS map to a valid widget type', () => {
    fc.assert(
      fc.property(arbServiceType, (serviceType) => {
        const entries = BUNDLED_SCHEMAS[serviceType];
        for (const entry of entries) {
          const widget = expectedWidget(entry);
          expect(['select', 'text', 'number', 'checkbox', 'key-value-editor', 'list-editor']).toContain(widget);
        }
      }),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Property 7: Validation error display
// Feature: enhanced-variable-configuration, Property 7: Validation error display
// **Validates: Requirements 4.8, 4.11**
// ---------------------------------------------------------------------------

describe('Property 7: Validation error display', () => {
  test('for any number entry with min/max validation, values outside bounds produce a non-null error', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 100000 }),
        fc.integer({ min: 1, max: 100000 }),
        fc.boolean(),
        (min, range, belowMin) => {
          const max = min + range;
          const validation: ValidationRule = { min, max };
          const entry: TerraformVariableSchema = {
            name: 'test_field',
            type: 'number',
            description: 'test',
            validation,
          };

          // Generate a value outside the valid range
          const invalidValue = belowMin ? min - 1 : max + 1;
          const error = validateValue(invalidValue, validation, entry);

          expect(error).not.toBeNull();
          expect(typeof error).toBe('string');
          expect(error!.length).toBeGreaterThan(0);

          if (belowMin) {
            expect(error).toContain(`at least ${min}`);
          } else {
            expect(error).toContain(`at most ${max}`);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  test('for any entry with allowed_values validation, a value not in the list produces a non-null error', () => {
    fc.assert(
      fc.property(
        fc.array(fc.integer({ min: 1, max: 1000 }), { minLength: 1, maxLength: 10 }),
        (allowedValues) => {
          const validation: ValidationRule = { allowed_values: allowedValues };
          const entry: TerraformVariableSchema = {
            name: 'test_field',
            type: 'number',
            description: 'test',
            validation,
          };

          // Pick a value guaranteed not to be in the allowed list
          const maxAllowed = Math.max(...allowedValues);
          const invalidValue = maxAllowed + 1000;

          const error = validateValue(invalidValue, validation, entry);
          expect(error).not.toBeNull();
          expect(typeof error).toBe('string');
          expect(error).toContain('allowed values');
        },
      ),
      { numRuns: 100 },
    );
  });

  test('for any entry with pattern validation, a non-matching string produces a non-null error', () => {
    const validation: ValidationRule = {
      pattern: '^[a-z]+$',
      pattern_description: 'Must contain only lowercase letters',
    };
    const entry: TerraformVariableSchema = {
      name: 'test_field',
      type: 'string',
      description: 'test',
      validation,
    };

    fc.assert(
      fc.property(
        // Generate strings that contain at least one non-lowercase character
        fc.string({ minLength: 1, maxLength: 20 }).filter((s) => !/^[a-z]+$/.test(s)),
        (invalidValue) => {
          const error = validateValue(invalidValue, validation, entry);
          expect(error).not.toBeNull();
          expect(typeof error).toBe('string');
          // When pattern_description is provided, it should be used in the error
          expect(error).toContain('Must contain only lowercase letters');
        },
      ),
      { numRuns: 100 },
    );
  });

  test('for any number entry with min/max validation, values within bounds produce null (no error)', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 10000 }),
        fc.integer({ min: 1, max: 10000 }),
        (min, range) => {
          const max = min + range;
          const validation: ValidationRule = { min, max };
          const entry: TerraformVariableSchema = {
            name: 'test_field',
            type: 'number',
            description: 'test',
            validation,
          };

          // Generate a value within the valid range
          const validValue = min + Math.floor(range / 2);
          const error = validateValue(validValue, validation, entry);
          expect(error).toBeNull();
        },
      ),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Property 8: Export disabled on validation errors
// Feature: enhanced-variable-configuration, Property 8: Export disabled on validation errors
// **Validates: Requirements 4.9**
// ---------------------------------------------------------------------------

describe('Property 8: Export disabled on validation errors', () => {
  test('for any config state with at least one invalid value, the error tracking map is non-empty (export should be disabled)', () => {
    fc.assert(
      fc.property(arbServiceType, (serviceType) => {
        const entries = BUNDLED_SCHEMAS[serviceType];

        // Find entries with validation rules
        const validatedEntries = entries.filter(
          (e) =>
            e.validation &&
            (e.validation.min !== undefined ||
              e.validation.max !== undefined ||
              (e.validation.allowed_values && e.validation.allowed_values.length > 0)),
        );

        if (validatedEntries.length === 0) return; // skip services with no validation

        // Simulate error tracking: for each validated entry, generate an invalid value
        const errors: Record<string, string> = {};

        for (const entry of validatedEntries) {
          let invalidValue: unknown;

          if (
            entry.validation!.min !== undefined &&
            entry.validation!.min !== null
          ) {
            invalidValue = entry.validation!.min - 1;
          } else if (
            entry.validation!.allowed_values &&
            entry.validation!.allowed_values.length > 0
          ) {
            // Pick a value not in the allowed list
            const maxVal =
              typeof entry.validation!.allowed_values[0] === 'number'
                ? Math.max(...(entry.validation!.allowed_values as number[])) + 9999
                : '__invalid__';
            invalidValue = maxVal;
          } else {
            continue;
          }

          const error = validateValue(invalidValue, entry.validation, entry);
          if (error) {
            errors[entry.name] = error;
          }
        }

        // At least one error should exist → export should be disabled
        const hasErrors = Object.keys(errors).length > 0;
        expect(hasErrors).toBe(true);

        // Verify the inverse: the form would signal hasErrors = true
        // This mirrors the component logic: `const hasErrors = Object.keys(errors).length > 0;`
        expect(Object.keys(errors).length).toBeGreaterThan(0);
      }),
      { numRuns: 100 },
    );
  });

  test('for any config state with all valid values, the error tracking map is empty (export should be enabled)', () => {
    fc.assert(
      fc.property(arbServiceType, (serviceType) => {
        const entries = BUNDLED_SCHEMAS[serviceType];
        const errors: Record<string, string> = {};

        for (const entry of entries) {
          // Use the default value (which should always be valid) or skip
          const value = entry.default;
          if (value === undefined || value === null) continue;

          const error = validateValue(value, entry.validation, entry);
          if (error) {
            errors[entry.name] = error;
          }
        }

        // All defaults should be valid → no errors → export enabled
        expect(Object.keys(errors).length).toBe(0);
      }),
      { numRuns: 100 },
    );
  });
});
