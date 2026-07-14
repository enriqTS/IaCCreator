/**
 * Routing Module — Barrel Export
 *
 * Re-exports all public functions and types from the routing submodules.
 * Consumers can import from `@/utils/routing` instead of individual files.
 */

// routing.ts — orthogonal waypoint helpers
export { inferAnchorPosition, MIN_OFFSET } from './routing';

// orthogonal-router.ts — primary obstacle-aware router
export { routeOrthogonalConnector, balancePath, shortDistanceRoute, filterObstaclesByProximity } from './orthogonal-router';
export type { RoutingRequest, RoutingResult } from './orthogonal-router';

// routing-grid.ts — visibility grid builder
export { buildRoutingSpots, inflateRect, rectsIntersect, extrudePoint } from './routing-grid';
export type { RoutingRect } from './routing-grid';

// routing-obstacles.ts — obstacle rect collection
export { boundsToRoutingRect, collectObstacles, pointToMinimalRect } from './routing-obstacles';

// routing-pathfinder.ts — Dijkstra pathfinder with bend penalty
export { findShortestPath, simplifyPath, findSpotIndex, anchorToExitDirection } from './routing-pathfinder';
export type { ObstacleRect, ExitDirection } from './routing-pathfinder';
