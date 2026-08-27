/**
 * Converting store state to and from its saved and exported shapes.
 */

import type { StateCreator } from 'zustand';
import type { AnchorRef, ArchitectureBlock, CanvasObject, Connector, GeometricObject, GeometricShape, LineObject, ObjectGroup, Point, RoutingMode, SemanticContainerObject, TextObject, UMLKind, UMLObject } from '@/types/diagram';
import { DEFAULT_BLOCK_VISUAL, DEFAULT_GEO_VISUAL, DEFAULT_LINE_VISUAL, DEFAULT_TEXT_VISUAL, DEFAULT_UML_VISUAL } from '@/types/diagram';
import type { DiagramState, SerializedCanvasObject } from '@/types/serialization';
import { CURRENT_DIAGRAM_VERSION } from '@/types/serialization';
import type { AnchorPosition } from '@/utils/anchor';
import { EMPTY_GLOBAL_CONFIG } from '@/types/terraform-variables';
import { normalizeSemanticZOrder } from '@/utils/semantic-containment';
import type { DiagramStore } from './store-types';

export interface SerializationSlice {
  // Serialization
  serializeDiagramState: () => DiagramState;
  loadDiagramState: (state: DiagramState) => void;
}

export const createSerializationSlice: StateCreator<DiagramStore, [], [], SerializationSlice> = (set, get) => ({
    // --- Serialization ---

    serializeDiagramState: (): DiagramState => {
      const { connectors, viewport, projectName, environments, canvasObjects, objectGroups, globalTerraformConfig } = get();

      const serializedCanvasObjects: SerializedCanvasObject[] = Array.from(canvasObjects.values()).map((obj) => {
        const base: SerializedCanvasObject = {
          id: obj.id,
          objectType: obj.objectType,
          name: obj.name,
          visualConfig: { ...obj.visualConfig } as Record<string, unknown>,
          zIndex: obj.zIndex,
          ...(obj.groupId !== undefined && { groupId: obj.groupId }),
          ...('parentContainerId' in obj && obj.parentContainerId !== undefined && { parentContainerId: obj.parentContainerId }),
        };

        if (obj.objectType === 'architecture-block') {
          base.x = obj.position.x;
          base.y = obj.position.y;
          base.serviceType = obj.serviceType;
          base.config = { ...obj.config };
          base.terraformVariables = { ...obj.terraformVariables };
          base.presentation = obj.presentation ?? 'node';
        } else if (obj.objectType === 'line') {
          base.startX = obj.start.x;
          base.startY = obj.start.y;
          base.endX = obj.end.x;
          base.endY = obj.end.y;
          base.sourceAnchorObjectId = obj.sourceAnchor ? obj.sourceAnchor.objectId : null;
          base.targetAnchorObjectId = obj.targetAnchor ? obj.targetAnchor.objectId : null;
          base.sourceAnchorPosition = obj.sourceAnchor ? obj.sourceAnchor.anchorPosition : null;
          base.targetAnchorPosition = obj.targetAnchor ? obj.targetAnchor.anchorPosition : null;
          if (obj.waypoints && obj.waypoints.length > 0) {
            base.waypoints = obj.waypoints.map((wp) => ({ x: wp.x, y: wp.y }));
          }
        } else if (obj.objectType === 'geometric') {
          base.x = obj.position.x;
          base.y = obj.position.y;
        } else if (obj.objectType === 'text') {
          base.x = obj.position.x;
          base.y = obj.position.y;
          base.content = obj.content;
        } else if (obj.objectType === 'semantic-container') {
          base.x = obj.position.x;
          base.y = obj.position.y;
          base.containerType = obj.containerType;
          base.config = { ...obj.config };
        } else if (obj.objectType === 'uml') {
          base.x = obj.position.x;
          base.y = obj.position.y;
          base.umlKind = obj.umlKind;
          if (obj.classData) {
            base.classData = { ...obj.classData, attributes: [...obj.classData.attributes], methods: [...obj.classData.methods] };
          }
        }

        return base;
      });

      const serializedGroups = Array.from(objectGroups.values()).map((g) => ({
        id: g.id,
        name: g.name,
        memberIds: [...g.memberIds],
      }));

      return {
        version: CURRENT_DIAGRAM_VERSION,
        projectName,
        environments: environments.map((e) => ({ ...e, variables: { ...e.variables } })),
        canvasObjects: serializedCanvasObjects,
        connectors: Array.from(connectors.values()).map((c) => ({
          id: c.id,
          sourceId: c.sourceId,
          targetId: c.targetId,
          connectionType: c.connectionType,
          ...(c.connectionConfig !== undefined && { connection_config: { ...c.connectionConfig } }),
          ...(c.origin !== undefined && { origin: c.origin }),
          ...(c.containerId !== undefined && { container_id: c.containerId }),
        })),
        viewport: { ...viewport },
        ...(serializedGroups.length > 0 && { objectGroups: serializedGroups }),
        globalTerraformConfig: { ...globalTerraformConfig },
        globalRoutingMode: get().globalRoutingMode,
      };
    },

    loadDiagramState: (state: DiagramState): void => {
      const connectorsMap = new Map<string, Connector>();
      for (const c of state.connectors) {
        connectorsMap.set(c.id, {
          id: c.id,
          sourceId: c.sourceId,
          targetId: c.targetId,
          connectionType: c.connectionType,
          ...(c.connection_config !== undefined && { connectionConfig: { ...c.connection_config } }),
          ...(c.origin !== undefined && { origin: c.origin }),
          ...(c.container_id !== undefined && { containerId: c.container_id }),
        });
      }

      // Deserialize canvasObjects
      const canvasObjectsMap = new Map<string, CanvasObject>();

      // Valid geometric shapes for fallback
      const VALID_GEOMETRIC_SHAPES: Set<string> = new Set([
        'rectangle', 'rounded-rectangle', 'ellipse', 'circle',
        'triangle', 'diamond', 'parallelogram', 'trapezoid',
        'hexagon', 'octagon', 'pentagon', 'star', 'cross',
        'arrow-right', 'arrow-left', 'arrow-up', 'arrow-down',
        'chevron', 'cylinder', 'cloud', 'callout',
        'document', 'process', 'decision', 'data', 'predefined-process',
      ]);

      const VALID_UML_KINDS: Set<string> = new Set([
        'class', 'interface', 'actor', 'use-case', 'component', 'package', 'node',
      ]);

      if (state.canvasObjects && state.canvasObjects.length > 0) {
        for (let i = 0; i < state.canvasObjects.length; i++) {
          const sObj = state.canvasObjects[i];
          const zIndex = (sObj as unknown as Record<string, unknown>).zIndex as number ?? i;
          const groupId = (sObj as unknown as Record<string, unknown>).groupId as string | undefined;
          if (sObj.objectType === 'architecture-block') {
            const obj: ArchitectureBlock = {
              id: sObj.id,
              objectType: 'architecture-block',
              name: sObj.name,
              position: { x: sObj.x ?? 0, y: sObj.y ?? 0 },
              serviceType: sObj.serviceType!,
              config: sObj.config ? { ...sObj.config } : {},
              terraformVariables: sObj.terraformVariables
                ? { ...sObj.terraformVariables }
                : {},
              visualConfig: {
                width: (sObj.visualConfig.width as number) ?? DEFAULT_BLOCK_VISUAL.width,
                height: (sObj.visualConfig.height as number) ?? DEFAULT_BLOCK_VISUAL.height,
              },
              zIndex,
              ...(groupId !== undefined && { groupId }),
              ...(sObj.parentContainerId != null && { parentContainerId: sObj.parentContainerId }),
              presentation: sObj.presentation ?? 'node',
            };
            canvasObjectsMap.set(obj.id, obj);
          } else if (sObj.objectType === 'line') {
            // v2→v3 migration: lines without anchor fields get null anchors
            const sourceAnchor: AnchorRef | null = sObj.sourceAnchorObjectId
              ? { objectId: sObj.sourceAnchorObjectId, anchorPosition: (sObj.sourceAnchorPosition as AnchorPosition) ?? 'right' }
              : null;
            const targetAnchor: AnchorRef | null = sObj.targetAnchorObjectId
              ? { objectId: sObj.targetAnchorObjectId, anchorPosition: (sObj.targetAnchorPosition as AnchorPosition) ?? 'left' }
              : null;
            // Deserialize waypoints: validate shape, treat malformed data as null
            let waypoints: Point[] | null = null;
            if (Array.isArray(sObj.waypoints)) {
              const valid = sObj.waypoints.every(
                (wp): wp is { x: number; y: number } =>
                  wp != null && typeof wp === 'object' && typeof wp.x === 'number' && typeof wp.y === 'number' && isFinite(wp.x) && isFinite(wp.y)
              );
              if (valid && sObj.waypoints.length > 0) {
                waypoints = sObj.waypoints.map((wp) => ({ x: wp.x, y: wp.y }));
              }
            }
            const obj: LineObject = {
              id: sObj.id,
              objectType: 'line',
              name: sObj.name,
              start: { x: sObj.startX ?? 0, y: sObj.startY ?? 0 },
              end: { x: sObj.endX ?? 0, y: sObj.endY ?? 0 },
              sourceAnchor,
              targetAnchor,
              waypoints,
              visualConfig: {
                color: (sObj.visualConfig.color as string) ?? DEFAULT_LINE_VISUAL.color,
                borderWidth: (sObj.visualConfig.borderWidth as number) ?? DEFAULT_LINE_VISUAL.borderWidth,
                strokeStyle: (sObj.visualConfig.strokeStyle as 'solid' | 'dashed') ?? DEFAULT_LINE_VISUAL.strokeStyle,
                startArrow: (sObj.visualConfig.startArrow as boolean) ?? DEFAULT_LINE_VISUAL.startArrow,
                endArrow: (sObj.visualConfig.endArrow as boolean) ?? DEFAULT_LINE_VISUAL.endArrow,
                routingMode: (sObj.visualConfig.routingMode as RoutingMode) ?? DEFAULT_LINE_VISUAL.routingMode,
              },
              zIndex,
              ...(groupId !== undefined && { groupId }),
            };
            canvasObjectsMap.set(obj.id, obj);
          } else if (sObj.objectType === 'geometric') {
            // Validate shape, fall back to rectangle for unknown shapes
            const rawShape = (sObj.visualConfig.shape as string) ?? DEFAULT_GEO_VISUAL.shape;
            const shape = VALID_GEOMETRIC_SHAPES.has(rawShape) ? rawShape as GeometricShape : 'rectangle';
            const obj: GeometricObject = {
              id: sObj.id,
              objectType: 'geometric',
              name: sObj.name,
              position: { x: sObj.x ?? 0, y: sObj.y ?? 0 },
              visualConfig: {
                width: (sObj.visualConfig.width as number) ?? DEFAULT_GEO_VISUAL.width,
                height: (sObj.visualConfig.height as number) ?? DEFAULT_GEO_VISUAL.height,
                fill: (sObj.visualConfig.fill as boolean) ?? DEFAULT_GEO_VISUAL.fill,
                fillColor: (sObj.visualConfig.fillColor as string) ?? DEFAULT_GEO_VISUAL.fillColor,
                borderColor: (sObj.visualConfig.borderColor as string) ?? DEFAULT_GEO_VISUAL.borderColor,
                borderWidth: (sObj.visualConfig.borderWidth as number) ?? DEFAULT_GEO_VISUAL.borderWidth,
                shape,
              },
              zIndex,
              ...(groupId !== undefined && { groupId }),
            };
            canvasObjectsMap.set(obj.id, obj);
          } else if (sObj.objectType === 'text') {
            const obj: TextObject = {
              id: sObj.id,
              objectType: 'text',
              name: sObj.name,
              position: { x: sObj.x ?? 0, y: sObj.y ?? 0 },
              content: sObj.content ?? '',
              visualConfig: {
                width: (sObj.visualConfig.width as number) ?? DEFAULT_TEXT_VISUAL.width,
                height: (sObj.visualConfig.height as number) ?? DEFAULT_TEXT_VISUAL.height,
                fontSize: (sObj.visualConfig.fontSize as number) ?? DEFAULT_TEXT_VISUAL.fontSize,
                fontColor: (sObj.visualConfig.fontColor as string) ?? DEFAULT_TEXT_VISUAL.fontColor,
                textAlign: (sObj.visualConfig.textAlign as 'left' | 'center' | 'right') ?? DEFAULT_TEXT_VISUAL.textAlign,
                bold: (sObj.visualConfig.bold as boolean) ?? DEFAULT_TEXT_VISUAL.bold,
                italic: (sObj.visualConfig.italic as boolean) ?? DEFAULT_TEXT_VISUAL.italic,
              },
              zIndex,
              ...(groupId !== undefined && { groupId }),
            };
            canvasObjectsMap.set(obj.id, obj);
          } else if (sObj.objectType === 'semantic-container') {
            const obj: SemanticContainerObject = {
              id: sObj.id,
              objectType: 'semantic-container',
              containerType: sObj.containerType ?? 'generic',
              name: sObj.name,
              position: { x: sObj.x ?? 0, y: sObj.y ?? 0 },
              config: { ...(sObj.config ?? {}) },
              visualConfig: {
                width: (sObj.visualConfig.width as number) ?? 480,
                height: (sObj.visualConfig.height as number) ?? 320,
                fillColor: (sObj.visualConfig.fillColor as string) ?? '#172033',
                borderColor: (sObj.visualConfig.borderColor as string) ?? '#64748b',
                borderWidth: (sObj.visualConfig.borderWidth as number) ?? 2,
              },
              zIndex,
              ...(groupId !== undefined && { groupId }),
              ...(sObj.parentContainerId != null && { parentContainerId: sObj.parentContainerId }),
            };
            canvasObjectsMap.set(obj.id, obj);
          } else if (sObj.objectType === 'uml') {
            // Validate umlKind, fall back to 'class' for unknown kinds (renders as generic rectangle)
            const rawKind = sObj.umlKind as string | undefined;
            const umlKind: UMLKind = (rawKind && VALID_UML_KINDS.has(rawKind)) ? rawKind as UMLKind : 'class';
            const obj: UMLObject = {
              id: sObj.id,
              objectType: 'uml',
              name: sObj.name,
              position: { x: sObj.x ?? 0, y: sObj.y ?? 0 },
              umlKind,
              classData: sObj.classData ? { ...sObj.classData, attributes: [...sObj.classData.attributes], methods: [...sObj.classData.methods] } : undefined,
              visualConfig: {
                width: (sObj.visualConfig.width as number) ?? DEFAULT_UML_VISUAL.width,
                height: (sObj.visualConfig.height as number) ?? DEFAULT_UML_VISUAL.height,
                fillColor: (sObj.visualConfig.fillColor as string) ?? DEFAULT_UML_VISUAL.fillColor,
                borderColor: (sObj.visualConfig.borderColor as string) ?? DEFAULT_UML_VISUAL.borderColor,
                borderWidth: (sObj.visualConfig.borderWidth as number) ?? DEFAULT_UML_VISUAL.borderWidth,
                headerColor: (sObj.visualConfig.headerColor as string) ?? DEFAULT_UML_VISUAL.headerColor,
              },
              zIndex,
              ...(groupId !== undefined && { groupId }),
            };
            canvasObjectsMap.set(obj.id, obj);
          } else {
            // Unknown objectType: skip with warning
            console.warn(`Unknown objectType "${sObj.objectType}" for object "${sObj.id}", skipping.`);
          }
        }
      }

      // Deserialize objectGroups
      const objectGroupsMap = new Map<string, ObjectGroup>();
      if (state.objectGroups && state.objectGroups.length > 0) {
        for (const g of state.objectGroups) {
          objectGroupsMap.set(g.id, {
            id: g.id,
            name: g.name,
            memberIds: [...g.memberIds],
          });
        }
      }

      set({
        connectors: connectorsMap,
        canvasObjects: normalizeSemanticZOrder(canvasObjectsMap),
        viewport: { ...state.viewport },
        projectName: state.projectName,
        environments: state.environments.map((e) => ({ ...e, variables: { ...e.variables } })),
        selectedObjectIds: new Set(),
        objectGroups: objectGroupsMap,
        globalTerraformConfig: state.globalTerraformConfig
          ? { ...state.globalTerraformConfig }
          : structuredClone(EMPTY_GLOBAL_CONFIG),
        globalRoutingMode: (state.globalRoutingMode as RoutingMode) ?? 'orthogonal',
        _undoStack: [],
        _redoStack: [],
        canUndo: false,
        canRedo: false,
      });
    },
});
