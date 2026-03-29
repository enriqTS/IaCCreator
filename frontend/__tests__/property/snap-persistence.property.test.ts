/**
 * Property-based test: Grid settings persistence round trip
 *
 * Feature: canvas-snap-to-grid, Property 9: Grid settings persistence round trip
 *
 * **Validates: Requirements 8.1, 8.2**
 *
 * For any valid grid cell size g (5 ≤ g ≤ 100) and any booleans for
 * snapToGridEnabled and alignmentGuidesEnabled, storing these values in the
 * layout preferences store and reading them back shall yield the same values.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import fc from 'fast-check';
import { useLayoutPreferencesStore } from '@/store/layout-preferences-store';

/** Arbitrary for valid grid cell sizes per the spec: integers in [5, 100]. */
const gridSizeArb = fc.integer({ min: 5, max: 100 });

describe('Feature: canvas-snap-to-grid, Property 9: Grid settings persistence round trip', () => {
  beforeEach(() => {
    // Reset store to defaults before each test
    const store = useLayoutPreferencesStore.getState();
    store.setGridCellSize(20);
    store.setSnapToGridEnabled(true);
    store.setAlignmentGuidesEnabled(true);
  });

  it('setGridCellSize round-trips for any valid size in [5, 100]', () => {
    /**
     * **Validates: Requirements 8.1, 8.2**
     *
     * Strategy: Generate random grid sizes in [5, 100], set via the store,
     * then read back and verify the value is identical.
     */
    fc.assert(
      fc.property(gridSizeArb, (gridSize) => {
        useLayoutPreferencesStore.getState().setGridCellSize(gridSize);
        const stored = useLayoutPreferencesStore.getState().gridCellSize;
        expect(stored).toBe(gridSize);
      }),
      { numRuns: 100 },
    );
  });

  it('setSnapToGridEnabled round-trips for any boolean', () => {
    /**
     * **Validates: Requirements 8.1, 8.2**
     *
     * Strategy: Generate random booleans, set via the store,
     * then read back and verify the value is identical.
     */
    fc.assert(
      fc.property(fc.boolean(), (enabled) => {
        useLayoutPreferencesStore.getState().setSnapToGridEnabled(enabled);
        const stored = useLayoutPreferencesStore.getState().snapToGridEnabled;
        expect(stored).toBe(enabled);
      }),
      { numRuns: 100 },
    );
  });

  it('setAlignmentGuidesEnabled round-trips for any boolean', () => {
    /**
     * **Validates: Requirements 8.1, 8.2**
     *
     * Strategy: Generate random booleans, set via the store,
     * then read back and verify the value is identical.
     */
    fc.assert(
      fc.property(fc.boolean(), (enabled) => {
        useLayoutPreferencesStore.getState().setAlignmentGuidesEnabled(enabled);
        const stored = useLayoutPreferencesStore.getState().alignmentGuidesEnabled;
        expect(stored).toBe(enabled);
      }),
      { numRuns: 100 },
    );
  });

  it('all grid settings round-trip together for any valid combination', () => {
    /**
     * **Validates: Requirements 8.1, 8.2**
     *
     * Strategy: Generate random valid grid size, snap boolean, and guides boolean
     * simultaneously. Set all three, then read all three back and verify equality.
     */
    fc.assert(
      fc.property(
        gridSizeArb,
        fc.boolean(),
        fc.boolean(),
        (gridSize, snapEnabled, guidesEnabled) => {
          const store = useLayoutPreferencesStore.getState();
          store.setGridCellSize(gridSize);
          store.setSnapToGridEnabled(snapEnabled);
          store.setAlignmentGuidesEnabled(guidesEnabled);

          const state = useLayoutPreferencesStore.getState();
          expect(state.gridCellSize).toBe(gridSize);
          expect(state.snapToGridEnabled).toBe(snapEnabled);
          expect(state.alignmentGuidesEnabled).toBe(guidesEnabled);
        },
      ),
      { numRuns: 100 },
    );
  });
});
