/**
 * Property-based test: Hollow click-through behavior
 *
 * **Validates: Requirements 6.1, 6.2**
 *
 * Property 7: Geometric objects with fill disabled have pointer-events none on
 * interior; objects with fill enabled capture all pointer events.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import fc from 'fast-check';
import { render, screen, cleanup } from '@testing-library/react';
import React from 'react';
import GeometricObjectComponent from '@/components/canvas/GeometricObjectComponent';
import { useDiagramStore } from '@/store/diagram-store';
import type { GeometricObject, GeometricShape } from '@/types/diagram';

/**
 * Arbitrary that generates a random GeometricObject with configurable fill.
 * Varies shape, dimensions, border widths, colors, and fill state.
 */
function geometricObjectArbitrary(fillOverride?: boolean): fc.Arbitrary<GeometricObject> {
  return fc.record({
    id: fc.uuid(),
    objectType: fc.constant('geometric' as const),
    name: fc.string({ minLength: 1, maxLength: 20 }),
    position: fc.record({
      x: fc.double({ min: 0, max: 2000, noNaN: true, noDefaultInfinity: true }),
      y: fc.double({ min: 0, max: 2000, noNaN: true, noDefaultInfinity: true }),
    }),
    visualConfig: fc.record({
      width: fc.integer({ min: 40, max: 800 }),
      height: fc.integer({ min: 40, max: 600 }),
      fill: fillOverride !== undefined ? fc.constant(fillOverride) : fc.boolean(),
      fillColor: fc.constantFrom('#3b82f6', '#ef4444', '#22c55e', '#f59e0b'),
      borderColor: fc.constantFrom('#ffffff', '#000000', '#6b7280'),
      borderWidth: fc.integer({ min: 1, max: 12 }),
      shape: fc.constantFrom<GeometricShape>('rectangle', 'ellipse'),
    }),
    zIndex: fc.integer({ min: 0, max: 1000 }),
    groupId: fc.constant(undefined),
  });
}

describe('Hollow Click-Through Property', () => {
  beforeEach(() => {
    useDiagramStore.setState({
      canvasObjects: new Map(),
      selectedObjectIds: new Set(),
      objectGroups: new Map(),
    });
    cleanup();
  });

  it('Property 7: hollow objects (fill: false) have pointer-events none on wrapper and interior, auto on border overlay', () => {
    /**
     * **Validates: Requirements 6.1, 6.2**
     *
     * For any geometric object with fill disabled, the outer wrapper and
     * interior div must have pointer-events: none, while the border overlay
     * must have pointer-events: auto so the border stroke remains clickable.
     */
    fc.assert(
      fc.property(geometricObjectArbitrary(false), (geoObj) => {
        cleanup();

        const { unmount } = render(
          React.createElement(GeometricObjectComponent, {
            object: geoObj,
            isSelected: false,
          }),
        );

        const wrapper = screen.getByTestId(`geometric-object-${geoObj.id}`);
        const interior = screen.getByTestId(`geometric-interior-${geoObj.id}`);
        const borderOverlay = screen.getByTestId(`geometric-border-overlay-${geoObj.id}`);

        expect(wrapper.style.pointerEvents).toBe('none');
        expect(interior.style.pointerEvents).toBe('none');
        expect(borderOverlay.style.pointerEvents).toBe('auto');

        unmount();
      }),
      { numRuns: 100 },
    );
  });

  it('Property 7b: filled objects (fill: true) have pointer-events auto on the main div', () => {
    /**
     * **Validates: Requirements 6.1, 6.2**
     *
     * For any geometric object with fill enabled, the main div must have
     * pointer-events: auto so the entire filled area captures clicks.
     */
    fc.assert(
      fc.property(geometricObjectArbitrary(true), (geoObj) => {
        cleanup();

        const { unmount } = render(
          React.createElement(GeometricObjectComponent, {
            object: geoObj,
            isSelected: false,
          }),
        );

        const mainDiv = screen.getByTestId(`geometric-object-${geoObj.id}`);
        expect(mainDiv.style.pointerEvents).toBe('auto');

        unmount();
      }),
      { numRuns: 100 },
    );
  });
});
