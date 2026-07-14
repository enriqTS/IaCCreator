'use client';

import { useMemo, useEffect, useState, useRef, useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { useLayoutPreferencesStore } from '@/store/layout-preferences-store';
import { useSnapDrag } from '@/hooks/useSnapDrag';
import { useConnectionLabel } from '@/hooks/useConnectionLabel';
import { useServiceNameLabels } from '@/hooks/useServiceNameLabels';
import { getAnchorPoints } from '@/utils/anchor';
import type { AnchorPosition } from '@/utils/anchor';
import { inferAnchorPosition, routeOrthogonalConnector, collectObstacles, boundsToRoutingRect, pointToMinimalRect } from '@/utils/routing';
import { getConnectionBounds, computeShapeEdgePoint } from '@/utils/bounds-utils';
import { getObjectBounds } from '@/types/diagram';
import type { LineObject, Point, CanvasObject } from '@/types/diagram';
import type { AlignmentGuide } from '@/utils/snap';
import { snapPointToGrid } from '@/utils/snap';
import { computeParallelIndex, applyParallelOffset } from '@/utils/parallel-offset';

interface LineObjectComponentProps {
  line: LineObject;
  isSelected: boolean;
  onAlignmentGuidesChange?: (guides: AlignmentGuide[]) => void;
}

const RECTANGULAR_SHAPES = new Set(['rectangle', 'rounded-rectangle', 'process']);

function needsRayIntersection(obj: CanvasObject): boolean {
  return obj.objectType === 'geometric' && !RECTANGULAR_SHAPES.has(obj.visualConfig.shape);
}

function getAnchorDirectionPoint(center: Point, anchorPosition: AnchorPosition): Point {
  const offset = 1000;
  switch (anchorPosition) {
    case 'top': return { x: center.x, y: center.y - offset };
    case 'right': return { x: center.x + offset, y: center.y };
    case 'bottom': return { x: center.x, y: center.y + offset };
    case 'left': return { x: center.x - offset, y: center.y };
  }
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
  const viewportScale = useDiagramStore((s) => s.viewport.scale);
  const updateLineLabelOffset = useDiagramStore((s) => s.updateLineLabelOffset);
  const updateLineCustomLabel = useDiagramStore((s) => s.updateLineCustomLabel);

  const { handleMouseDown, alignmentGuides, distributionGuides } = useSnapDrag({
    objectId: line.id,
    isSelected,
    locked: line.locked,
  });

  // Lift alignment guides up to parent (ElementLayer) since we can't render
  // the AlignmentGuides SVG component inside an SVG <g> element
  useEffect(() => {
    onAlignmentGuidesChange?.(alignmentGuides);
  }, [alignmentGuides, onAlignmentGuidesChange]);

  // Resolve connection label and dashed override from connector config
  const { label: connectionLabel, dashed: connectionDashed } = useConnectionLabel(line);

  // Effective label: custom label overrides connector-derived label
  const effectiveLabel = line.customLabel ?? connectionLabel;

  // Label position with offset support
  const labelOffset = line.labelOffset ?? { x: 0, y: 0 };

  // Label editing state
  const [isEditingLabel, setIsEditingLabel] = useState(false);
  const [editLabelValue, setEditLabelValue] = useState('');
  const labelInputRef = useRef<HTMLInputElement>(null);
  const labelDragRef = useRef<{ startX: number; startY: number; startOffset: Point } | null>(null);

  // Focus the input when entering edit mode
  useEffect(() => {
    if (isEditingLabel && labelInputRef.current) {
      labelInputRef.current.focus();
      labelInputRef.current.select();
    }
  }, [isEditingLabel]);

  // Handle label double-click to start editing
  const handleLabelDoubleClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    setEditLabelValue(effectiveLabel ?? '');
    setIsEditingLabel(true);
  }, [effectiveLabel]);

  // Handle label edit commit
  const handleLabelEditCommit = useCallback(() => {
    setIsEditingLabel(false);
    const trimmed = editLabelValue.trim();
    updateLineCustomLabel(line.id, trimmed || null);
  }, [editLabelValue, line.id, updateLineCustomLabel]);

  // Handle label drag for offset
  const handleLabelDragStart = useCallback((e: React.PointerEvent) => {
    if (line.locked) return;
    e.stopPropagation();
    e.preventDefault();

    const startX = e.clientX;
    const startY = e.clientY;
    labelDragRef.current = { startX, startY, startOffset: { ...labelOffset } };

    const handleMove = (ev: PointerEvent) => {
      if (!labelDragRef.current) return;
      const dx = (ev.clientX - labelDragRef.current.startX) / viewportScale;
      const dy = (ev.clientY - labelDragRef.current.startY) / viewportScale;
      updateLineLabelOffset(line.id, {
        x: labelDragRef.current.startOffset.x + dx,
        y: labelDragRef.current.startOffset.y + dy,
      });
    };

    const handleUp = () => {
      labelDragRef.current = null;
      window.removeEventListener('pointermove', handleMove);
      window.removeEventListener('pointerup', handleUp);
    };

    window.addEventListener('pointermove', handleMove);
    window.addEventListener('pointerup', handleUp);
  }, [line.id, line.locked, labelOffset, viewportScale, updateLineLabelOffset]);

  // Get service name label bounding boxes for knockout masks
  const serviceNameLabels = useServiceNameLabels();

  // Determine if the knockout mask should be applied
  const hasMask = !!(effectiveLabel || serviceNameLabels.length > 0);

  const { color, borderWidth, strokeStyle, startArrow, endArrow, routingMode } = line.visualConfig;

  // Compute actual endpoints, resolving anchors when present using fixed anchor positions
  let startPt = line.start;
  let endPt = line.end;

  if (line.sourceAnchor) {
    const sourceObj = canvasObjects.get(line.sourceAnchor.objectId);
    if (sourceObj) {
      if (needsRayIntersection(sourceObj)) {
        const anchorDir = getAnchorDirectionPoint(sourceObj.position, line.sourceAnchor.anchorPosition);
        startPt = computeShapeEdgePoint(sourceObj, anchorDir);
      } else {
        const bounds = getConnectionBounds(sourceObj);
        startPt = getAnchorPoints(bounds)[line.sourceAnchor.anchorPosition];
      }
    }
  }

  if (line.targetAnchor) {
    const targetObj = canvasObjects.get(line.targetAnchor.objectId);
    if (targetObj) {
      if (needsRayIntersection(targetObj)) {
        const anchorDir = getAnchorDirectionPoint(targetObj.position, line.targetAnchor.anchorPosition);
        endPt = computeShapeEdgePoint(targetObj, anchorDir);
      } else {
        const bounds = getConnectionBounds(targetObj);
        endPt = getAnchorPoints(bounds)[line.targetAnchor.anchorPosition];
      }
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
    // Snap all endpoints to grid to avoid diagonals (anchored or not)
    const effectiveStart = snapToGridEnabled
      ? snapPointToGrid(startPt, gridCellSize) : startPt;
    const effectiveEnd = snapToGridEnabled
      ? snapPointToGrid(endPt, gridCellSize) : endPt;

    // If user-modified waypoints exist, use them directly
    if (line.waypoints && line.waypoints.length > 0) {
      return [effectiveStart, ...line.waypoints, effectiveEnd];
    }

    // Compute orthogonal waypoints when routing mode requires it
    if (useOrthogonal === true) {
      // Determine anchor positions: use actual anchors when present, infer for unanchored ends
      const startPos = line.sourceAnchor
        ? line.sourceAnchor.anchorPosition
        : inferAnchorPosition(effectiveStart, effectiveEnd);
      const endPos = line.targetAnchor
        ? line.targetAnchor.anchorPosition
        : inferAnchorPosition(effectiveEnd, effectiveStart);

      // Collect obstacles (all non-line objects except source and target)
      const sourceObjId = line.sourceAnchor?.objectId;
      const targetObjId = line.targetAnchor?.objectId;
      const excludeIds = new Set<string>(
        [line.id, sourceObjId, targetObjId].filter((id): id is string => id != null)
      );
      const obstacles = collectObstacles(canvasObjects, excludeIds);

      // Get bounding rects for source and target shapes
      const sourceObj = sourceObjId ? canvasObjects.get(sourceObjId) : undefined;
      const targetObj = targetObjId ? canvasObjects.get(targetObjId) : undefined;
      const sourceRect = sourceObj
        ? boundsToRoutingRect(getObjectBounds(sourceObj))
        : pointToMinimalRect(effectiveStart);
      const targetRect = targetObj
        ? boundsToRoutingRect(getObjectBounds(targetObj))
        : pointToMinimalRect(effectiveEnd);

      const result = routeOrthogonalConnector({
        sourcePoint: effectiveStart,
        sourceSide: startPos,
        sourceRect,
        targetPoint: effectiveEnd,
        targetSide: endPos,
        targetRect,
        obstacles,
        shapeMargin: snapToGridEnabled ? gridCellSize : 20,
        gridSize: snapToGridEnabled ? gridCellSize : undefined,
      });

      return [effectiveStart, ...result.waypoints, effectiveEnd];
    }

    return [effectiveStart, effectiveEnd];
  }, [useOrthogonal, startPt, endPt, line.sourceAnchor, line.targetAnchor, line.waypoints, line.id, canvasObjects, snapToGridEnabled, gridCellSize]);

  // Apply parallel offset for lines connecting the same object pair
  const offsetPathPoints = useMemo((): Point[] => {
    const sourceObjId = line.sourceAnchor?.objectId;
    const targetObjId = line.targetAnchor?.objectId;
    const parallelIdx = computeParallelIndex(line.id, sourceObjId, targetObjId, canvasObjects);
    if (parallelIdx === 0) return pathPoints;
    return applyParallelOffset(pathPoints, parallelIdx);
  }, [pathPoints, line.id, line.sourceAnchor?.objectId, line.targetAnchor?.objectId, canvasObjects]);

  const pathD = useMemo(() => buildPathD(offsetPathPoints), [offsetPathPoints]);

  // Override strokeStyle to dashed when connector schema says so (e.g., authorizer connections)
  const effectiveStrokeStyle = connectionDashed ? 'dashed' : strokeStyle;
  const dashArray = effectiveStrokeStyle === 'dashed' ? `${borderWidth * 3} ${borderWidth * 2}` : undefined;
  const arrowSize = Math.max(borderWidth * 3, 6);

  // Hit area width: constant 20 screen pixels, scaled inversely with zoom
  const hitWidth = Math.max(20 / viewportScale, borderWidth + 10);

  // Build a shortened path for the visible line so arrows sit flush at endpoints
  const visiblePathD = useMemo(() => {
    const shortened = shortenPath(offsetPathPoints, startArrow ? arrowSize : 0, endArrow ? arrowSize : 0);
    return buildPathD(shortened);
  }, [offsetPathPoints, startArrow, endArrow, arrowSize]);

  // Diagonal mode: compute shortened endpoints for the visible line
  // Must be called unconditionally (before any conditional return) to satisfy React's Rules of Hooks
  const diagShortened = useMemo(() => {
    return shortenPath([startPt, endPt], startArrow ? arrowSize : 0, endArrow ? arrowSize : 0);
  }, [startPt, endPt, startArrow, endArrow, arrowSize]);

  const markerId = `line-${line.id}`;
  const startMarkerId = `${markerId}-start`;
  const endMarkerId = `${markerId}-end`;

  // Midpoint for lock indicator — use the geometric center of the path
  const midIdx = Math.floor(offsetPathPoints.length / 2);
  const midPt = offsetPathPoints.length % 2 === 1
    ? offsetPathPoints[midIdx]
    : {
        x: (offsetPathPoints[midIdx - 1].x + offsetPathPoints[midIdx].x) / 2,
        y: (offsetPathPoints[midIdx - 1].y + offsetPathPoints[midIdx].y) / 2,
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
          strokeWidth={hitWidth}
          fill="none"
          onMouseDown={handleMouseDown}
        />

        {/* Selection indicator — border-only outline matching text box style */}
        {isSelected && (
          <path
            d={pathD}
            stroke="rgba(59, 130, 246, 0.7)"
            strokeWidth={borderWidth + 3}
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
            pointerEvents="none"
            mask={hasMask ? `url(#label-mask-${line.id})` : undefined}
          />
        )}

        {/* Main visible path — masked to create knockout behind label */}
        <path
          d={visiblePathD}
          stroke={color}
          strokeWidth={borderWidth}
          strokeDasharray={dashArray}
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
          pointerEvents="none"
          markerStart={startArrow ? `url(#${startMarkerId})` : undefined}
          markerEnd={endArrow ? `url(#${endMarkerId})` : undefined}
          mask={hasMask ? `url(#label-mask-${line.id})` : undefined}
        />

        {/* Knockout mask: hides the line behind the label area */}
        {hasMask && (
          <defs>
            <mask id={`label-mask-${line.id}`} maskUnits="userSpaceOnUse" x="-99999" y="-99999" width="199998" height="199998">
              {/* White = show everything */}
              <rect x="-99999" y="-99999" width="199998" height="199998" fill="white" />
              {/* Black rect at connection label position = hide line there */}
              {effectiveLabel && (
                <rect
                  x={midPt.x + labelOffset.x - (effectiveLabel.length * 3.5 + 8)}
                  y={midPt.y + labelOffset.y - 12}
                  width={effectiveLabel.length * 7 + 16}
                  height={20}
                  rx={4}
                  ry={4}
                  fill="black"
                />
              )}
              {/* Service name label knockouts */}
              {serviceNameLabels.map((rect) => (
                <rect
                  key={rect.id}
                  x={rect.x}
                  y={rect.y}
                  width={rect.width}
                  height={rect.height}
                  fill="black"
                />
              ))}
            </mask>
          </defs>
        )}

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

        {/* Connection label — text only, line and glow are knocked out behind it via mask */}
        {effectiveLabel && !isEditingLabel && (
          <>
            {/* Selection border around label */}
            {isSelected && (
              <rect
                x={midPt.x + labelOffset.x - (effectiveLabel.length * 3.5 + 8)}
                y={midPt.y + labelOffset.y - 12}
                width={effectiveLabel.length * 7 + 16}
                height={20}
                rx={4}
                ry={4}
                fill="none"
                stroke="rgba(59, 130, 246, 0.7)"
                strokeWidth={1.5}
                pointerEvents="none"
              />
            )}
            {/* Invisible hit area for clicking/dragging the label */}
            <rect
              x={midPt.x + labelOffset.x - (effectiveLabel.length * 3.5 + 6)}
              y={midPt.y + labelOffset.y - 10}
              width={effectiveLabel.length * 7 + 12}
              height={16}
              fill="transparent"
              className="cursor-grab"
              onPointerDown={handleLabelDragStart}
              onDoubleClick={handleLabelDoubleClick}
            />
            <text
              x={midPt.x + labelOffset.x}
              y={midPt.y + labelOffset.y + 3}
              textAnchor="middle"
              fontSize="11"
              fontFamily="sans-serif"
              fill="#ffffff"
              className="cursor-grab"
              onPointerDown={handleLabelDragStart}
              onDoubleClick={handleLabelDoubleClick}
              style={{ userSelect: 'none' }}
            >
              {effectiveLabel}
            </text>
          </>
        )}
        {/* Inline label editor */}
        {isEditingLabel && (
          <foreignObject
            x={midPt.x + labelOffset.x - 60}
            y={midPt.y + labelOffset.y - 12}
            width={120}
            height={24}
          >
            <input
              ref={labelInputRef}
              type="text"
              value={editLabelValue}
              onChange={(e) => setEditLabelValue(e.target.value)}
              onBlur={handleLabelEditCommit}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleLabelEditCommit();
                if (e.key === 'Escape') setIsEditingLabel(false);
                e.stopPropagation();
              }}
              className="w-full h-full text-center text-xs bg-neutral-800 text-white border border-blue-500 rounded px-1 outline-none"
              style={{ fontSize: '11px' }}
            />
          </foreignObject>
        )}
      </g>
    );
  }

  // Diagonal mode (or free-floating): render straight <line>
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
        strokeWidth={hitWidth}
        onMouseDown={handleMouseDown}
      />

      {/* Selection indicator — border-only outline matching text box style */}
      {isSelected && (
        <line
          x1={startPt.x}
          y1={startPt.y}
          x2={endPt.x}
          y2={endPt.y}
          stroke="rgba(59, 130, 246, 0.7)"
          strokeWidth={borderWidth + 3}
          strokeLinecap="round"
          pointerEvents="none"
          mask={hasMask ? `url(#label-mask-${line.id})` : undefined}
        />
      )}

      {/* Main visible line — shortened to make room for arrows, masked for label knockout */}
      <line
        x1={diagShortened[0].x}
        y1={diagShortened[0].y}
        x2={diagShortened[1].x}
        y2={diagShortened[1].y}
        stroke={color}
        strokeWidth={borderWidth}
        strokeDasharray={dashArray}
        strokeLinecap="round"
        pointerEvents="none"
        markerStart={startArrow ? `url(#${startMarkerId})` : undefined}
        markerEnd={endArrow ? `url(#${endMarkerId})` : undefined}
        mask={hasMask ? `url(#label-mask-${line.id})` : undefined}
      />

      {/* Knockout mask for diagonal line */}
      {hasMask && (
        <defs>
          <mask id={`label-mask-${line.id}`} maskUnits="userSpaceOnUse" x="-99999" y="-99999" width="199998" height="199998">
            <rect x="-99999" y="-99999" width="199998" height="199998" fill="white" />
            {connectionLabel && (
              <rect
                x={midPt.x - (connectionLabel.length * 3.5 + 8)}
                y={midPt.y - 12}
                width={connectionLabel.length * 7 + 16}
                height={20}
                rx={4}
                ry={4}
                fill="black"
              />
            )}
            {/* Service name label knockouts */}
            {serviceNameLabels.map((rect) => (
              <rect
                key={rect.id}
                x={rect.x}
                y={rect.y}
                width={rect.width}
                height={rect.height}
                fill="black"
              />
            ))}
          </mask>
        </defs>
      )}

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

      {/* Connection label — text only, line and glow are knocked out behind it via mask */}
      {connectionLabel && (
        <>
          {/* Selection border around label */}
          {isSelected && (
            <rect
              x={midPt.x - (connectionLabel.length * 3.5 + 8)}
              y={midPt.y - 12}
              width={connectionLabel.length * 7 + 16}
              height={20}
              rx={4}
              ry={4}
              fill="none"
              stroke="rgba(59, 130, 246, 0.7)"
              strokeWidth={1.5}
              pointerEvents="none"
            />
          )}
          {/* Invisible hit area for clicking the label to select the line */}
          <rect
            x={midPt.x - (connectionLabel.length * 3.5 + 6)}
            y={midPt.y - 10}
            width={connectionLabel.length * 7 + 12}
            height={16}
            fill="transparent"
            className="cursor-pointer"
            onMouseDown={handleMouseDown}
          />
          <text
            x={midPt.x}
            y={midPt.y + 3}
            textAnchor="middle"
            fontSize="11"
            fontFamily="sans-serif"
            fill="#ffffff"
            className="cursor-pointer"
            onMouseDown={handleMouseDown}
            style={{ userSelect: 'none' }}
          >
            {connectionLabel}
          </text>
        </>
      )}
    </g>
  );
}
