import type { GeometricShape, Rect, CanvasObject, Point } from '@/types/diagram';
import { getObjectBounds } from '@/types/diagram';
import { SHAPE_PATH_REGISTRY } from '@/utils/shape-paths';
import { rayRectIntersection } from '@/utils/anchor';

/**
 * Shapes that are inherently circular/elliptical and should use
 * ellipse-based bounding box calculations.
 */
const ELLIPSE_SHAPES: Set<GeometricShape> = new Set(['circle', 'ellipse']);

/**
 * Shapes considered "rectangular" — use standard bounding-box anchor logic.
 */
const RECTANGULAR_SHAPES: Set<GeometricShape> = new Set(['rectangle', 'rounded-rectangle', 'process']);

/**
 * Parse an SVG path string and extract sampled points along the path,
 * including control points for curves and arc extremes.
 *
 * Supports: M, L, Z, A, Q, C commands (absolute only, which is what
 * SHAPE_PATH_REGISTRY produces).
 */
function samplePathPoints(pathD: string): Array<{ x: number; y: number }> {
  const points: Array<{ x: number; y: number }> = [];

  // Tokenize: split into commands and their numeric arguments
  const tokens = pathD.match(/[MLZAQC]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?/g);
  if (!tokens) return points;

  let currentCommand = '';
  let nums: number[] = [];
  let currentX = 0;
  let currentY = 0;

  function flush() {
    switch (currentCommand) {
      case 'M':
      case 'L': {
        // Each pair is a point
        for (let i = 0; i < nums.length - 1; i += 2) {
          const x = nums[i];
          const y = nums[i + 1];
          points.push({ x, y });
          currentX = x;
          currentY = y;
        }
        break;
      }
      case 'Q': {
        // Quadratic bezier: control point + end point (pairs of 4)
        for (let i = 0; i < nums.length - 3; i += 4) {
          const cpx = nums[i];
          const cpy = nums[i + 1];
          const endX = nums[i + 2];
          const endY = nums[i + 3];
          // Sample the control point and endpoint for bounds
          points.push({ x: cpx, y: cpy });
          points.push({ x: endX, y: endY });
          // Also sample midpoints for tighter bounds
          points.push({ x: (currentX + 2 * cpx + endX) / 4, y: (currentY + 2 * cpy + endY) / 4 });
          points.push({ x: (currentX + cpx) / 2, y: (currentY + cpy) / 2 });
          points.push({ x: (cpx + endX) / 2, y: (cpy + endY) / 2 });
          currentX = endX;
          currentY = endY;
        }
        break;
      }
      case 'C': {
        // Cubic bezier: cp1, cp2, end (groups of 6)
        for (let i = 0; i < nums.length - 5; i += 6) {
          const cp1x = nums[i];
          const cp1y = nums[i + 1];
          const cp2x = nums[i + 2];
          const cp2y = nums[i + 3];
          const endX = nums[i + 4];
          const endY = nums[i + 5];
          // Sample control points, midpoints, and endpoints for bounds
          points.push({ x: cp1x, y: cp1y });
          points.push({ x: cp2x, y: cp2y });
          points.push({ x: endX, y: endY });
          // Sample additional points along the curve (t=0.25, 0.5, 0.75)
          for (const t of [0.25, 0.5, 0.75]) {
            const mt = 1 - t;
            const x = mt * mt * mt * currentX + 3 * mt * mt * t * cp1x + 3 * mt * t * t * cp2x + t * t * t * endX;
            const y = mt * mt * mt * currentY + 3 * mt * mt * t * cp1y + 3 * mt * t * t * cp2y + t * t * t * endY;
            points.push({ x, y });
          }
          currentX = endX;
          currentY = endY;
        }
        break;
      }
      case 'A': {
        // Arc: rx ry xRotation largeArcFlag sweepFlag endX endY (groups of 7)
        for (let i = 0; i < nums.length - 6; i += 7) {
          const rx = nums[i];
          const ry = nums[i + 1];
          // xRotation = nums[i + 2] — unused for axis-aligned arcs
          // largeArcFlag = nums[i + 3]
          // sweepFlag = nums[i + 4]
          const endX = nums[i + 5];
          const endY = nums[i + 6];

          // For arcs, compute the center and sample extremes
          const cx = (currentX + endX) / 2;
          const cy = (currentY + endY) / 2;

          // Add arc endpoint
          points.push({ x: endX, y: endY });

          // Sample the ellipse extremes (top, bottom, left, right)
          points.push({ x: cx - rx, y: cy });
          points.push({ x: cx + rx, y: cy });
          points.push({ x: cx, y: cy - ry });
          points.push({ x: cx, y: cy + ry });

          // Additional samples along the arc
          for (const t of [0.25, 0.5, 0.75]) {
            const angle = t * Math.PI * 2;
            points.push({ x: cx + rx * Math.cos(angle), y: cy + ry * Math.sin(angle) });
          }

          currentX = endX;
          currentY = endY;
        }
        break;
      }
      case 'Z':
        // Close path — no new points
        break;
    }
    nums = [];
  }

  for (const token of tokens) {
    if (/^[MLZAQC]$/.test(token)) {
      flush();
      currentCommand = token;
    } else {
      nums.push(parseFloat(token));
    }
  }
  flush();

  return points;
}

/**
 * Compute a tight axis-aligned bounding box for a geometric shape,
 * including stroke width. Returns a Rect relative to the shape's
 * local coordinate system (where the shape's position is its center).
 *
 * - For circles/ellipses: uses the analytical ellipse bounding box + borderWidth/2
 * - For polygons/other shapes: samples path vertices and computes tight AABB + borderWidth/2
 * - Falls back to rectangle bounds if shape path not found in registry
 */
export function getShapeTightBounds(
  shape: GeometricShape,
  width: number,
  height: number,
  borderWidth: number
): Rect {
  const halfStroke = borderWidth / 2;

  // Ellipse/circle: use analytical bounding box
  if (ELLIPSE_SHAPES.has(shape)) {
    return getEllipseBounds(width, height, halfStroke);
  }

  // Try to get path from registry
  const pathFn = SHAPE_PATH_REGISTRY[shape];
  if (!pathFn) {
    // Fallback: rectangle bounds
    return getRectangleBounds(width, height, halfStroke);
  }

  // Generate path and sample vertices
  const pathD = pathFn(width, height);
  const points = samplePathPoints(pathD);

  if (points.length === 0) {
    return getRectangleBounds(width, height, halfStroke);
  }

  // Compute tight AABB from sampled points
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  for (const p of points) {
    if (p.x < minX) minX = p.x;
    if (p.y < minY) minY = p.y;
    if (p.x > maxX) maxX = p.x;
    if (p.y > maxY) maxY = p.y;
  }

  // Expand by half stroke width on each side
  minX -= halfStroke;
  minY -= halfStroke;
  maxX += halfStroke;
  maxY += halfStroke;

  return {
    x: minX,
    y: minY,
    width: maxX - minX,
    height: maxY - minY,
  };
}

/**
 * Ellipse bounding box: centered in the width×height space,
 * expanded by halfStroke on each side.
 */
function getEllipseBounds(width: number, height: number, halfStroke: number): Rect {
  // The ellipse is centered at (width/2, height/2) with radii (width/2, height/2)
  // For a circle, r = min(width, height) / 2, centered at (width/2, height/2)
  return {
    x: 0 - halfStroke,
    y: 0 - halfStroke,
    width: width + 2 * halfStroke,
    height: height + 2 * halfStroke,
  };
}

/**
 * Rectangle fallback bounds: full width×height + halfStroke.
 */
function getRectangleBounds(width: number, height: number, halfStroke: number): Rect {
  return {
    x: 0 - halfStroke,
    y: 0 - halfStroke,
    width: width + 2 * halfStroke,
    height: height + 2 * halfStroke,
  };
}


/**
 * Get the bounding rect to use for connection line termination.
 * For geometric objects, returns tight shape bounds in canvas coordinates.
 * For all other object types, falls back to the standard `getObjectBounds`.
 *
 * This ensures connection lines terminate at the visible edge of geometric shapes
 * (circles, triangles, etc.) rather than at an oversized default rectangle.
 */
export function getConnectionBounds(obj: CanvasObject): Rect {
  if (obj.objectType === 'geometric') {
    const { width, height, borderWidth, shape } = obj.visualConfig;
    const tightBounds = getShapeTightBounds(shape, width, height, borderWidth);

    // Convert from local coordinates (0,0 = top-left of shape area)
    // to canvas coordinates (position is center of shape)
    return {
      x: obj.position.x - width / 2 + tightBounds.x,
      y: obj.position.y - height / 2 + tightBounds.y,
      width: tightBounds.width,
      height: tightBounds.height,
    };
  }

  return getObjectBounds(obj);
}



/**
 * Compute where a ray from the center of a geometric shape to an external point
 * intersects the shape's visible edge. For non-rectangular shapes, this finds the
 * actual perimeter point rather than a bounding-box cardinal midpoint.
 *
 * Falls back to rayRectIntersection for rectangular shapes or on failure.
 */
export function computeShapeEdgePoint(
  obj: CanvasObject,
  externalPoint: Point
): Point {
  if (obj.objectType !== 'geometric') {
    return rayRectIntersection(getConnectionBounds(obj), externalPoint);
  }

  const { width, height, shape } = obj.visualConfig;

  if (RECTANGULAR_SHAPES.has(shape)) {
    return rayRectIntersection(getConnectionBounds(obj), externalPoint);
  }

  const cx = obj.position.x;
  const cy = obj.position.y;
  const dx = externalPoint.x - cx;
  const dy = externalPoint.y - cy;

  if (dx === 0 && dy === 0) {
    return { x: cx, y: cy };
  }

  // For circles/ellipses: analytical ray-ellipse intersection
  if (ELLIPSE_SHAPES.has(shape)) {
    const rx = width / 2;
    const ry = height / 2;
    const angle = Math.atan2(dy, dx);
    return {
      x: cx + rx * Math.cos(angle),
      y: cy + ry * Math.sin(angle),
    };
  }

  // For polygon shapes: intersect ray with path line segments
  const pathFn = SHAPE_PATH_REGISTRY[shape];
  if (!pathFn) {
    return rayRectIntersection(getConnectionBounds(obj), externalPoint);
  }

  const pathD = pathFn(width, height);
  const segments = extractLineSegments(pathD, width, height);

  if (segments.length === 0) {
    return rayRectIntersection(getConnectionBounds(obj), externalPoint);
  }

  // Ray from center (in local coords: width/2, height/2) toward externalPoint
  const localCx = width / 2;
  const localCy = height / 2;
  // Convert external point to local coordinates
  const localExtX = externalPoint.x - (cx - width / 2);
  const localExtY = externalPoint.y - (cy - height / 2);
  const rdx = localExtX - localCx;
  const rdy = localExtY - localCy;

  let bestT = Infinity;

  for (const seg of segments) {
    const t = raySegmentIntersection(localCx, localCy, rdx, rdy, seg[0], seg[1], seg[2], seg[3]);
    if (t !== null && t > 0 && t < bestT) {
      bestT = t;
    }
  }

  if (!isFinite(bestT)) {
    return rayRectIntersection(getConnectionBounds(obj), externalPoint);
  }

  // Convert back to canvas coordinates
  const localHitX = localCx + bestT * rdx;
  const localHitY = localCy + bestT * rdy;
  return {
    x: cx - width / 2 + localHitX,
    y: cy - height / 2 + localHitY,
  };
}

/**
 * Extract line segments from an SVG path string (M/L/Z commands only).
 * Returns array of [x1, y1, x2, y2] segments.
 */
function extractLineSegments(pathD: string, _w: number, _h: number): Array<[number, number, number, number]> {
  const segments: Array<[number, number, number, number]> = [];
  const tokens = pathD.match(/[MLZAQC]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?/g);
  if (!tokens) return segments;

  let cmd = '';
  let nums: number[] = [];
  let curX = 0, curY = 0;
  let startX = 0, startY = 0;
  let prevX = 0, prevY = 0;

  function flush() {
    switch (cmd) {
      case 'M':
        for (let i = 0; i < nums.length - 1; i += 2) {
          if (i > 0) {
            segments.push([prevX, prevY, nums[i], nums[i + 1]]);
          }
          prevX = nums[i]; prevY = nums[i + 1];
          if (i === 0) { startX = prevX; startY = prevY; }
        }
        curX = prevX; curY = prevY;
        break;
      case 'L':
        for (let i = 0; i < nums.length - 1; i += 2) {
          segments.push([curX, curY, nums[i], nums[i + 1]]);
          curX = nums[i]; curY = nums[i + 1];
        }
        prevX = curX; prevY = curY;
        break;
      case 'Z':
        if (curX !== startX || curY !== startY) {
          segments.push([curX, curY, startX, startY]);
        }
        curX = startX; curY = startY;
        prevX = curX; prevY = curY;
        break;
    }
    nums = [];
  }

  for (const token of tokens) {
    if (/^[MLZAQC]$/.test(token)) {
      flush();
      cmd = token;
    } else {
      nums.push(parseFloat(token));
    }
  }
  flush();
  return segments;
}

/**
 * Ray-segment intersection. Ray starts at (ox, oy) with direction (dx, dy).
 * Segment from (x1, y1) to (x2, y2).
 * Returns t (ray parameter) if intersection exists, null otherwise.
 */
function raySegmentIntersection(
  ox: number, oy: number, dx: number, dy: number,
  x1: number, y1: number, x2: number, y2: number
): number | null {
  const sx = x2 - x1;
  const sy = y2 - y1;
  const denom = dx * sy - dy * sx;
  if (Math.abs(denom) < 1e-10) return null;

  const t = ((x1 - ox) * sy - (y1 - oy) * sx) / denom;
  const u = ((x1 - ox) * dy - (y1 - oy) * dx) / denom;

  if (t > 1e-10 && u >= 0 && u <= 1) {
    return t;
  }
  return null;
}
