'use client';

import { useRef, useState, useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { useLayoutPreferencesStore } from '@/store/layout-preferences-store';
import {
  snapToGrid,
  constrainToAxis,
  detectAlignmentGuides,
  applyAlignmentSnap,
  detectDistributionGuides,
  applyDistributionSnap,
} from '@/utils/snap';
import type { AlignmentGuide, DistributionGuide } from '@/utils/snap';
import { getObjectBounds } from '@/types/diagram';
import type { Point, Rect, CanvasObject } from '@/types/diagram';

const ALIGNMENT_THRESHOLD = 10;

/**
 * Compute the candidate bounding rect for an object at a given candidate center position.
 * For line objects, shifts the bounding box by the delta from the current midpoint.
 */
function computeCandidateBounds(obj: CanvasObject, candidatePos: Point): Rect {
  if (obj.objectType === 'line') {
    const midX = (obj.start.x + obj.end.x) / 2;
    const midY = (obj.start.y + obj.end.y) / 2;
    const dx = candidatePos.x - midX;
    const dy = candidatePos.y - midY;
    const bounds = getObjectBounds(obj);
    return {
      x: bounds.x + dx,
      y: bounds.y + dy,
      width: bounds.width,
      height: bounds.height,
    };
  }
  // For non-line objects, position is center
  const vc = obj.visualConfig as { width: number; height: number };
  return {
    x: candidatePos.x - vc.width / 2,
    y: candidatePos.y - vc.height / 2,
    width: vc.width,
    height: vc.height,
  };
}

export interface UseSnapDragOptions {
  objectId: string;
  isSelected: boolean;
  locked?: boolean;
  onDragStart?: () => void;
  onDragEnd?: () => void;
}

export interface UseSnapDragResult {
  handleMouseDown: (e: React.MouseEvent) => void;
  alignmentGuides: AlignmentGuide[];
  distributionGuides: DistributionGuide[];
}

export function useSnapDrag(options: UseSnapDragOptions): UseSnapDragResult {
  const { objectId, isSelected, locked, onDragStart, onDragEnd } = options;

  const [alignmentGuides, setAlignmentGuides] = useState<AlignmentGuide[]>([]);
  const [distributionGuides, setDistributionGuides] = useState<DistributionGuide[]>([]);

  const isDragging = useRef(false);
  const didDrag = useRef(false);
  const lastMouse = useRef<{ x: number; y: number } | null>(null);

  // Accumulated raw canvas delta since drag start (before snapping)
  const rawAccum = useRef<Point>({ x: 0, y: 0 });
  // The object's position at drag start (center for non-line objects)
  const startPosition = useRef<Point>({ x: 0, y: 0 });
  // Last snapped position applied — used to compute effective delta
  const lastSnappedPosition = useRef<Point>({ x: 0, y: 0 });

  const altHeld = useRef(false);
  const shiftHeld = useRef(false);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (e.button !== 0) return;

      const store = useDiagramStore.getState();

      // In placement mode, let the DragSizingOverlay handle the mousedown
      const tool = store.activeTool;
      if (
        typeof tool === 'object' &&
        (tool.type === 'place-service' || tool.type === 'place-shape' || tool.type === 'place-uml')
      ) {
        return;
      }

      // Locked: allow selection but prevent drag
      if (locked) {
        e.stopPropagation();
        if (e.shiftKey) {
          store.toggleObjectSelection(objectId);
        } else {
          store.selectObject(objectId);
        }
        return;
      }

      e.stopPropagation();
      store.beginDragGesture();

      // If shift is not held and the object is not already selected, select immediately
      if (!e.shiftKey && !isSelected) {
        store.selectObject(objectId);
      }

      isDragging.current = true;
      didDrag.current = false;
      lastMouse.current = { x: e.clientX, y: e.clientY };
      rawAccum.current = { x: 0, y: 0 };

      // Capture the primary object's start position
      const obj = useDiagramStore.getState().canvasObjects.get(objectId);
      if (obj) {
        if (obj.objectType === 'line') {
          // Use midpoint for lines
          startPosition.current = {
            x: (obj.start.x + obj.end.x) / 2,
            y: (obj.start.y + obj.end.y) / 2,
          };
        } else {
          startPosition.current = { ...obj.position };
        }
      }
      lastSnappedPosition.current = { ...startPosition.current };

      altHeld.current = e.altKey;
      shiftHeld.current = e.shiftKey;

      onDragStart?.();

      const viewport = useDiagramStore.getState().viewport;

      const handleKeyDown = (ev: KeyboardEvent) => {
        if (ev.key === 'Alt') altHeld.current = true;
        if (ev.key === 'Shift') shiftHeld.current = true;
      };

      const handleKeyUp = (ev: KeyboardEvent) => {
        if (ev.key === 'Alt') altHeld.current = false;
        if (ev.key === 'Shift') shiftHeld.current = false;
      };

      const handleBlur = () => {
        altHeld.current = false;
        shiftHeld.current = false;
      };

      const handleMouseMove = (ev: MouseEvent) => {
        if (!isDragging.current || !lastMouse.current) return;

        const rawDx = (ev.clientX - lastMouse.current.x) / viewport.scale;
        const rawDy = (ev.clientY - lastMouse.current.y) / viewport.scale;
        lastMouse.current = { x: ev.clientX, y: ev.clientY };

        if (rawDx === 0 && rawDy === 0) return;
        didDrag.current = true;

        // Update alt/shift from the mouse event itself
        altHeld.current = ev.altKey;
        shiftHeld.current = ev.shiftKey;

        // Accumulate raw delta
        rawAccum.current = {
          x: rawAccum.current.x + rawDx,
          y: rawAccum.current.y + rawDy,
        };

        const prefs = useLayoutPreferencesStore.getState();
        const snapEnabled = prefs.snapToGridEnabled && !altHeld.current;
        const guidesEnabled = prefs.alignmentGuidesEnabled && !altHeld.current;
        const gridSize = prefs.gridCellSize;

        let accum = { ...rawAccum.current };

        // Apply shift-axis constraint
        if (shiftHeld.current) {
          const constrained = constrainToAxis(accum.x, accum.y);
          accum = { x: constrained.dx, y: constrained.dy };
        }

        // Compute the candidate position for the primary object
        let candidatePos: Point = {
          x: startPosition.current.x + accum.x,
          y: startPosition.current.y + accum.y,
        };

        let currentGuides: AlignmentGuide[] = [];
        let currentDistGuides: DistributionGuide[] = [];

        if (snapEnabled) {
          // Snap to grid first
          candidatePos = {
            x: snapToGrid(candidatePos.x, gridSize),
            y: snapToGrid(candidatePos.y, gridSize),
          };

          // Detect alignment guides if enabled
          if (guidesEnabled) {
            const currentStore = useDiagramStore.getState();
            const primaryObj = currentStore.canvasObjects.get(objectId);

            if (primaryObj) {
              // Compute candidate bounds for the primary object
              const candidateBounds = computeCandidateBounds(primaryObj, candidatePos);

              // Gather bounds of all other non-selected objects
              const selectedIds = currentStore.selectedObjectIds;
              const otherBounds: Rect[] = [];
              for (const [id, obj] of currentStore.canvasObjects) {
                if (!selectedIds.has(id)) {
                  otherBounds.push(getObjectBounds(obj));
                }
              }

              currentGuides = detectAlignmentGuides(
                candidateBounds,
                otherBounds,
                ALIGNMENT_THRESHOLD,
              );

              // Apply alignment snap if guides found
              if (currentGuides.length > 0) {
                candidatePos = applyAlignmentSnap(candidatePos, currentGuides);
              }

              // Detect distribution (equal-spacing) guides
              const updatedBounds = computeCandidateBounds(primaryObj, candidatePos);
              currentDistGuides = detectDistributionGuides(
                updatedBounds,
                otherBounds,
                ALIGNMENT_THRESHOLD,
              );

              // Apply distribution snap if no alignment guides took effect on that axis
              if (currentDistGuides.length > 0) {
                const hasHAlign = currentGuides.some((g) => g.axis === 'vertical');
                const hasVAlign = currentGuides.some((g) => g.axis === 'horizontal');
                const filteredDist = currentDistGuides.filter((g) =>
                  g.axis === 'horizontal' ? !hasHAlign : !hasVAlign,
                );
                if (filteredDist.length > 0) {
                  candidatePos = applyDistributionSnap(candidatePos, filteredDist);
                }
              }
            }
          }
        }

        // Hide guides when Alt is held
        if (altHeld.current) {
          currentGuides = [];
          currentDistGuides = [];
        }

        setAlignmentGuides(currentGuides);
        setDistributionGuides(currentDistGuides);

        // Compute effective delta from last snapped position
        const effectiveDx = candidatePos.x - lastSnappedPosition.current.x;
        const effectiveDy = candidatePos.y - lastSnappedPosition.current.y;
        lastSnappedPosition.current = { ...candidatePos };

        if (effectiveDx !== 0 || effectiveDy !== 0) {
          useDiagramStore.getState().moveSelectedObjects(effectiveDx, effectiveDy);
        }
      };

      const handleMouseUp = (ev: MouseEvent) => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
        window.removeEventListener('keydown', handleKeyDown);
        window.removeEventListener('keyup', handleKeyUp);
        window.removeEventListener('blur', handleBlur);

        isDragging.current = false;
        lastMouse.current = null;
        setAlignmentGuides([]);
        setDistributionGuides([]);

        // Final snap: ensure the object's stored position is grid-aligned
        const prefs = useLayoutPreferencesStore.getState();
        if (didDrag.current && prefs.snapToGridEnabled) {
          const store = useDiagramStore.getState();
          const obj = store.canvasObjects.get(objectId);
          if (obj && obj.objectType !== 'line') {
            const snappedX = snapToGrid(obj.position.x, prefs.gridCellSize);
            const snappedY = snapToGrid(obj.position.y, prefs.gridCellSize);
            if (snappedX !== obj.position.x || snappedY !== obj.position.y) {
              store.moveSelectedObjects(snappedX - obj.position.x, snappedY - obj.position.y);
            }
          }
        }

        if (!didDrag.current) {
          // It was a click, not a drag
          const currentStore = useDiagramStore.getState();
          if (ev.shiftKey) {
            currentStore.toggleObjectSelection(objectId);
          } else {
            currentStore.selectObject(objectId);
          }
        }

        onDragEnd?.();
      };

      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      window.addEventListener('keydown', handleKeyDown);
      window.addEventListener('keyup', handleKeyUp);
      window.addEventListener('blur', handleBlur);
    },
    [objectId, isSelected, locked, onDragStart, onDragEnd],
  );

  return { handleMouseDown, alignmentGuides, distributionGuides };
}
