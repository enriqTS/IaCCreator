'use client';

import { useMemo, useEffect } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { useLayoutPreferencesStore } from '@/store/layout-preferences-store';
import { useSnapDrag } from '@/hooks/useSnapDrag';
import { getAnchorPoints } from '@/utils/anchor';
import { computeOrthogonalWaypoints, inferAnchorPosition } from '@/utils/routing';
import { getObjectBounds } from '@/types/diagram';
import type { LineObject, Point } from '@/types/diagram';
import type { AlignmentGuide } from '@/utils/snap';

interface LineObjectComponentProps {
  line: LineObject;
  isSelected: boolean;
  onAlignmentGuidesChange?: (guides: AlignmentGuide[]) => void;
}

/** Build an SVG path `d` attribute from an array of points using M and L commands */
function buildPathD(points: Point[]): string {
  if (points.length === 0) return '';
  const [first, ...rest] = points;
  return `M ${first.x} ${first.y}` + rest.map((p) => ` L ${p.x} ${p.y}`).join('');
}

/**
 * Shorten a path by pulling the first and/or last point inward along its segment.
 * This makes room for arrow markers so the line doesn't poke through the arrowhead.
 */
function shortenPath(points: Point[], startInset: number, endInset: number): Point[] {
  if (points.length < 2) return points;
  const result = [...points];

  if (startInset > 0) {
    const a = result[0];
    const b = result[1];
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const len = Math.sqrt(dx * dx + dy * dy);
    if (len > startInset) {
      result[0] = { x: a.x + (dx / len) * startInset, y: a.y + (dy / len) * startInset };
    }
  }

  if (endInset > 0) {
    const last = result.length - 1;
    const a = result[last];
    const b = result[last - 1];
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const len = Math.sqrt(dx * dx + dy * dy);
    if (len > endInset) {
      result[last] = { x: a.x + (dx / len) * endInset, y: a.y + (dy / len) * endInset };
    }
  }

  return result;
}

export default function LineObjectComponent({ line, isSelected, onAlignmentGuidesChange }: LineObjectComponentProps) {
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);

  const { handleMouseDown, alignmentGuides } = useSnapDrag({
    objectId: line.id,
    isSelected,
    locked: line.locked,
  });

  // Lift alignment guides up to parent (ElementLayer) since we can't render
  // the AlignmentGuides SVG component inside an SVG <g> element
  useEffect(() => {
    onAlignmentGuidesChange?.(alignmentGuides);
  }, [alignmentGuides, onAlignmentGuidesChange]);

  const { color, borderWidth, strokeStyle, startArrow, endArrow, routingMode } = line.visualConfig;

  // Compute actual endpoints, resolving anchors when present using fixed anchor positions
  let startPt = line.start;
  let endPt = line.end;

  if (line.sourceAnchor) {
    const sourceObj = canvasObjects.get(line.sourceAnchor.objectId);
    if (sourceObj) {
      const bounds = getObjectBounds(sourceObj);
      startPt = getAnchorPoints(bounds)[line.sourceAnchor.anchorPosition];
    }
  }

  if (line.targetAnchor) {
    const targetObj = canvasObjects.get(line.targetAnchor.objectId);
    if (targetObj) {
      const bounds = getObjectBounds(targetObj);
      endPt = getAnchorPoints(bounds)[line.targetAnchor.anchorPosition];
    }
  }

  // Determine if we should use orthogonal routing:
  // Applies whenever routingMode is 'orthogonal', regardless of anchor state
  const useOrthogonal = routingMode === 'orthogonal';

  // Read snap settings for grid-aware routing
  const snapToGridEnabled = useLayoutPreferencesStore((s) => s.snapToGridEnabled);
  const gridCellSize = useLayoutPreferencesStore((s) => s.gridCellSize);

  // Compute the full path points (start + waypoints + end)
  const pathPoints = useMemo((): Point[] => {
    // If user-modified waypoints exist, use them directly
    if (line.waypoints && line.waypoints.length > 0) {
      return [startPt, ...line.waypoints, endPt];
    }

    if (useOrthogonal) {
      // Determine anchor positions: use actual anchors when present, infer for unanchored ends
      const startPos = line.sourceAnchor
        ? line.sourceAnchor.anchorPosition
        : inferAnchorPosition(startPt, endPt);
      const endPos = line.targetAnchor
        ? line.targetAnchor.anchorPosition
        : inferAnchorPosition(endPt, startPt);

      const waypoints = computeOrthogonalWaypoints(
        startPt,
        startPos,
        endPt,
        endPos,
        undefined,
        snapToGridEnabled ? gridCellSize : undefined,
      );
      return [startPt, ...waypoints, endPt];
    }

    return [startPt, endPt];
  }, [useOrthogonal, startPt, endPt, line.sourceAnchor, line.targetAnchor, line.waypoints, snapToGridEnabled, gridCellSize]);

  const pathD = useMemo(() => buildPathD(pathPoints), [pathPoints]);

  const dashArray = strokeStyle === 'dashed' ? `${borderWidth * 3} ${borderWidth * 2}` : undefined;
  const arrowSize = Math.max(borderWidth * 3, 6);

  // Build a shortened path for the visible line so arrows sit flush at endpoints
  const visiblePathD = useMemo(() => {
    const shortened = shortenPath(pathPoints, startArrow ? arrowSize : 0, endArrow ? arrowSize : 0);
    return buildPathD(shortened);
  }, [pathPoints, startArrow, endArrow, arrowSize]);

  const markerId = `line-${line.id}`;
  const startMarkerId = `${markerId}-start`;
  const endMarkerId = `${markerId}-end`;

  // Midpoint for lock indicator — use the geometric center of the path
  const midIdx = Math.floor(pathPoints.length / 2);
  const midPt = pathPoints.length % 2 === 1
    ? pathPoints[midIdx]
    : {
        x: (pathPoints[midIdx - 1].x + pathPoints[midIdx].x) / 2,
        y: (pathPoints[midIdx - 1].y + pathPoints[midIdx].y) / 2,
      };

  // Render orthogonal path (SVG <path>) or diagonal line (SVG <line>)
  if (useOrthogonal) {
    return (
      <g data-testid={`line-object-${line.id}`} data-object-id={line.id} className="pointer-events-auto" style={{ cursor: line.locked ? 'not-allowed' : 'pointer' }}>
        <defs>
          {startArrow && (
            <marker
              id={startMarkerId}
              markerWidth={arrowSize}
              markerHeight={arrowSize}
              refX={arrowSize}
              refY={arrowSize / 2}
              orient="auto"
              markerUnits="userSpaceOnUse"
            >
              <path
                d={`M ${arrowSize} 0 L 0 ${arrowSize / 2} L ${arrowSize} ${arrowSize} Z`}
                fill={color}
                stroke="none"
              />
            </marker>
          )}
          {endArrow && (
            <marker
              id={endMarkerId}
              markerWidth={arrowSize}
              markerHeight={arrowSize}
              refX={0}
              refY={arrowSize / 2}
              orient="auto"
              markerUnits="userSpaceOnUse"
            >
              <path
                d={`M 0 0 L ${arrowSize} ${arrowSize / 2} L 0 ${arrowSize} Z`}
                fill={color}
                stroke="none"
              />
            </marker>
          )}
        </defs>

        {/* Invisible wider hit area for easier clicking — follows full path */}
        <path
          d={pathD}
          stroke="transparent"
          strokeWidth={Math.max(borderWidth + 10, 12)}
          fill="none"
          onMouseDown={handleMouseDown}
        />

        {/* Selection highlight glow — follows full path */}
        {isSelected && (
          <path
            d={pathD}
            stroke="rgba(59, 130, 246, 0.5)"
            strokeWidth={borderWidth + 6}
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
          />
        )}

        {/* Main visible path */}
        <path
          d={visiblePathD}
          stroke={color}
          strokeWidth={borderWidth}
          strokeDasharray={dashArray}
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
          markerStart={startArrow ? `url(#${startMarkerId})` : undefined}
          markerEnd={endArrow ? `url(#${endMarkerId})` : undefined}
        />

        {/* Lock indicator */}
        {line.locked && (
          <text
            data-testid={`lock-badge-${line.id}`}
            x={midPt.x}
            y={midPt.y - 8}
            textAnchor="middle"
            fontSize="12"
            style={{ pointerEvents: 'none', userSelect: 'none' }}
          >
            🔒
          </text>
        )}
      </g>
    );
  }

  // Diagonal mode (or free-floating): render straight <line>
  // Compute shortened endpoints for the visible line
  const diagShortened = useMemo(() => {
    return shortenPath([startPt, endPt], startArrow ? arrowSize : 0, endArrow ? arrowSize : 0);
  }, [startPt, endPt, startArrow, endArrow, arrowSize]);

  return (
    <g data-testid={`line-object-${line.id}`} data-object-id={line.id} className="pointer-events-auto" style={{ cursor: line.locked ? 'not-allowed' : 'pointer' }}>
      <defs>
        {startArrow && (
          <marker
            id={startMarkerId}
            markerWidth={arrowSize}
            markerHeight={arrowSize}
            refX={arrowSize}
            refY={arrowSize / 2}
            orient="auto"
            markerUnits="userSpaceOnUse"
          >
            <path
              d={`M ${arrowSize} 0 L 0 ${arrowSize / 2} L ${arrowSize} ${arrowSize} Z`}
              fill={color}
              stroke="none"
            />
          </marker>
        )}
        {endArrow && (
          <marker
            id={endMarkerId}
            markerWidth={arrowSize}
            markerHeight={arrowSize}
            refX={0}
            refY={arrowSize / 2}
            orient="auto"
            markerUnits="userSpaceOnUse"
          >
            <path
              d={`M 0 0 L ${arrowSize} ${arrowSize / 2} L 0 ${arrowSize} Z`}
              fill={color}
              stroke="none"
            />
          </marker>
        )}
      </defs>

      {/* Invisible wider hit area for easier clicking */}
      <line
        x1={startPt.x}
        y1={startPt.y}
        x2={endPt.x}
        y2={endPt.y}
        stroke="transparent"
        strokeWidth={Math.max(borderWidth + 10, 12)}
        onMouseDown={handleMouseDown}
      />

      {/* Selection highlight glow */}
      {isSelected && (
        <line
          x1={startPt.x}
          y1={startPt.y}
          x2={endPt.x}
          y2={endPt.y}
          stroke="rgba(59, 130, 246, 0.5)"
          strokeWidth={borderWidth + 6}
          strokeLinecap="round"
        />
      )}

      {/* Main visible line — shortened to make room for arrows */}
      <line
        x1={diagShortened[0].x}
        y1={diagShortened[0].y}
        x2={diagShortened[1].x}
        y2={diagShortened[1].y}
        stroke={color}
        strokeWidth={borderWidth}
        strokeDasharray={dashArray}
        strokeLinecap="round"
        markerStart={startArrow ? `url(#${startMarkerId})` : undefined}
        markerEnd={endArrow ? `url(#${endMarkerId})` : undefined}
      />

      {/* Lock indicator at midpoint */}
      {line.locked && (
        <text
          data-testid={`lock-badge-${line.id}`}
          x={midPt.x}
          y={midPt.y - 8}
          textAnchor="middle"
          fontSize="12"
          style={{ pointerEvents: 'none', userSelect: 'none' }}
        >
          🔒
        </text>
      )}
    </g>
  );
}
