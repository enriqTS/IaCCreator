import fc from 'fast-check';
import { describe, it, expect } from 'vitest';
import { shouldShowLabel } from '@/components/canvas/objects/ArchitectureBlockComponent';

/**
 * Feature: canvas-objects-editor, Property 2: Label visibility depends on name value
 * **Validates: Requirements 1.2, 1.3**
 */
describe('Property 2: Label visibility depends on name value', () => {
  it('shouldShowLabel returns false for empty, whitespace-only, and "Service" names, true otherwise', () => {
    fc.assert(
      fc.property(
        fc.oneof(
          // Names that should NOT show a label
          fc.constant(''),
          fc.constant('Service'),
          fc.integer({ min: 1, max: 10 }).map((n) => ' '.repeat(n)), // whitespace-only
          // Names that SHOULD show a label
          fc.string({ minLength: 1, maxLength: 50 }).filter((s) => s.trim() !== '' && s.trim() !== 'Service'),
        ),
        (name) => {
          const result = shouldShowLabel(name);
          const trimmed = name.trim();

          if (trimmed === '' || trimmed === 'Service') {
            expect(result).toBe(false);
          } else {
            expect(result).toBe(true);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
