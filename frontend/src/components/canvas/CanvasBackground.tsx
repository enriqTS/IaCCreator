'use client';

import { useRef, useEffect, useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import { useLayoutPreferencesStore } from '@/store/layout-preferences-store';
import type { Viewport, CanvasObject } from '@/types/diagram';
import { getObjectBounds } from '@/types/diagram';

const DOT_RADIUS = 1;
const DOT_COLOR_ACTIVE = 'rgba(255, 255, 255, 0.15)';
const DOT_COLOR_INACTIVE = 'rgba(255, 255, 255, 0.07)';

const CONNECTOR_COLOR = 'rgba(255, 255, 255, 0.5)';
const CONNECTOR_SELECTED_COLOR = 'rgba(59, 130, 246, 0.8)';
const CONNECTOR_LINE_WIDTH = 2;
const CONNECTOR_SELECTED_LINE_WIDTH = 3;
const ARROWHEAD_SIZE = 10;
const CLICK_TOLERANCE = 8;

/**
 * Compute the perpendicular distance from point P to the line segment AB.
 */
function pointToSegmentDistance(
  px: number,
  py: number,
  ax: number,
  ay: number,
  bx: number,
  by: number,
): number {
  const dx = bx - ax;
  const dy = by - ay;
  const lenSq = dx * dx + dy * dy;

  if (lenSq === 0) {
    // Segment is a point
    const ex = px - ax;
    const ey = py - ay;
    return Math.sqrt(ex * ex + ey * ey);
  }

  // Project P onto the line, clamping t to [0, 1]
  let t = ((px - ax) * dx + (py - ay) * dy) / lenSq;
  t = Math.max(0, Math.min(1, t));

  const closestX = ax + t * dx;
  const closestY = ay + t * dy;
  const ex = px - closestX;
  const ey = py - closestY;
  return Math.sqrt(ex * ex + ey * ey);
}

/**
 * Get the screen-space center of a canvas object.
 */
function getObjectScreenCenter(
  obj: CanvasObject,
  viewport: Viewport,
): { x: number; y: number } {
  const bounds = getObjectBounds(obj);
  const centerX = bounds.x + bounds.width / 2;
  const centerY = bounds.y + bounds.height / 2;
  return {
    x: centerX * viewport.scale + viewport.offsetX,
    y: centerY * viewport.scale + viewport.offsetY,
  };
}

/**
 * Draw an arrowhead at the target end of a line.
 */
function drawArrowhead(
  ctx: CanvasRenderingContext2D,
  fromX: number,
  fromY: number,
  toX: number,
  toY: number,
  size: number,
  color: string,
) {
  const angle = Math.atan2(toY - fromY, toX - fromX);
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(toX, toY);
  ctx.lineTo(
    toX - size * Math.cos(angle - Math.PI / 6),
    toY - size * Math.sin(angle - Math.PI / 6),
  );
  ctx.lineTo(
    toX - size * Math.cos(angle + Math.PI / 6),
    toY - size * Math.sin(angle + Math.PI / 6),
  );
  ctx.closePath();
  ctx.fill();
}

export default function CanvasBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const ctxRef = useRef<CanvasRenderingContext2D | null>(null);
  const rafRef = useRef<number>(0);

  const viewport = useDiagramStore((s) => s.viewport);
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);
  const connectors = useDiagramStore((s) => s.connectors);
  const selectedConnectorId = useDiagramStore((s) => s.selectedConnectorId);
  const selectConnector = useDiagramStore((s) => s.selectConnector);
  const gridCellSize = useLayoutPreferencesStore((s) => s.gridCellSize);
  const snapToGridEnabled = useLayoutPreferencesStore((s) => s.snapToGridEnabled);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = ctxRef.current;
    if (!canvas || !ctx) return;

    const { width, height } = canvas;
    const { offsetX, offsetY, scale } = viewport;

    ctx.clearRect(0, 0, width, height);

    // --- Draw grid dots ---
    const scaledSpacing = gridCellSize * scale;

    if (scaledSpacing >= 4) {
      const startCanvasX = Math.floor(-offsetX / scaledSpacing) * scaledSpacing + offsetX;
      const startCanvasY = Math.floor(-offsetY / scaledSpacing) * scaledSpacing + offsetY;

      ctx.fillStyle = snapToGridEnabled ? DOT_COLOR_ACTIVE : DOT_COLOR_INACTIVE;

      for (let sx = startCanvasX; sx < width; sx += scaledSpacing) {
        for (let sy = startCanvasY; sy < height; sy += scaledSpacing) {
          ctx.beginPath();
          ctx.arc(sx, sy, DOT_RADIUS, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    }

    // --- Draw connectors ---
    for (const connector of connectors.values()) {
      const sourceObj = canvasObjects.get(connector.sourceId);
      const targetObj = canvasObjects.get(connector.targetId);
      if (!sourceObj || !targetObj) continue;

      const source = getObjectScreenCenter(sourceObj, viewport);
      const target = getObjectScreenCenter(targetObj, viewport);

      const isSelected = connector.id === selectedConnectorId;
      const color = isSelected ? CONNECTOR_SELECTED_COLOR : CONNECTOR_COLOR;
      const lineWidth = isSelected ? CONNECTOR_SELECTED_LINE_WIDTH : CONNECTOR_LINE_WIDTH;

      // Draw line
      ctx.strokeStyle = color;
      ctx.lineWidth = lineWidth;
      ctx.beginPath();
      ctx.moveTo(source.x, source.y);
      ctx.lineTo(target.x, target.y);
      ctx.stroke();

      // Draw arrowhead at target end
      drawArrowhead(ctx, source.x, source.y, target.x, target.y, ARROWHEAD_SIZE, color);
    }
  }, [viewport, canvasObjects, connectors, selectedConnectorId, gridCellSize, snapToGridEnabled]);

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;

      // Check if click is near any connector line
      for (const connector of connectors.values()) {
        const sourceObj = canvasObjects.get(connector.sourceId);
        const targetObj = canvasObjects.get(connector.targetId);
        if (!sourceObj || !targetObj) continue;

        const source = getObjectScreenCenter(sourceObj, viewport);
        const target = getObjectScreenCenter(targetObj, viewport);

        const dist = pointToSegmentDistance(
          clickX,
          clickY,
          source.x,
          source.y,
          target.x,
          target.y,
        );

        if (dist <= CLICK_TOLERANCE) {
          selectConnector(connector.id);
          return;
        }
      }
    },
    [connectors, canvasObjects, viewport, selectConnector],
  );

  // Resize canvas to match its CSS size (keep 1:1 pixel ratio)
  const resizeCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;

    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.scale(dpr, dpr);
      ctxRef.current = ctx;
    }
  }, []);

  // Set up canvas context and resize listener
  useEffect(() => {
    resizeCanvas();

    const handleResize = () => {
      resizeCanvas();
      cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(draw);
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(rafRef.current);
    };
  }, [resizeCanvas, draw]);

  // Redraw on viewport/element/connector changes
  useEffect(() => {
    cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(draw);
  }, [draw]);

  return (
    <canvas
      ref={canvasRef}
      onClick={handleClick}
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        display: 'block',
      }}
    />
  );
}
