'use client';

import { useState, useCallback } from 'react';
import { useDiagramStore } from '@/store/diagram-store';
import ArchitectureBlockComponent from './objects/ArchitectureBlockComponent';
import LineObjectComponent from './objects/LineObjectComponent';
import GeometricObjectComponent from './objects/GeometricObjectComponent';
import TextObjectComponent from './objects/TextObjectComponent';
import UMLObjectComponent from './objects/UMLObjectComponent';
import SemanticContainerComponent from './objects/SemanticContainerComponent';
import ResizeHandles from './interactions/ResizeHandles';
import GroupBoundingBox from './interactions/GroupBoundingBox';
import AnchorIndicators from './interactions/AnchorIndicators';
import AlignmentGuides from './interactions/AlignmentGuides';
import { getObjectBounds } from '@/types/diagram';
import { getAnchorPoints } from '@/utils/anchor';
import type { AnchorPosition } from '@/utils/anchor';
import type { AlignmentGuide } from '@/utils/snap';

const ANCHOR_POSITIONS_LIST: AnchorPosition[] = ['top', 'right', 'bottom', 'left'];

export default function ElementLayer() {
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);
  const selectedObjectIds = useDiagramStore((s) => s.selectedObjectIds);
  const objectGroups = useDiagramStore((s) => s.objectGroups);
  const activeTool = useDiagramStore((s) => s.activeTool);

  const [hoveredObjectId, setHoveredObjectId] = useState<string | null>(null);

  // Track alignment guides from line objects (they render inside SVG and can't
  // render the AlignmentGuides component inline like non-line objects do)
  const [lineAlignmentGuides, setLineAlignmentGuides] = useState<AlignmentGuide[]>([]);
  const lineGuidesCallback = useCallback((guides: AlignmentGuide[]) => {
    setLineAlignmentGuides(guides);
  }, []);

  // Track hover via event delegation on the container
  const handleMouseOver = useCallback((e: React.MouseEvent) => {
    let target = e.target as HTMLElement | null;
    while (target && target !== e.currentTarget) {
      const objectId = target.getAttribute('data-object-id');
      if (objectId) {
        setHoveredObjectId(objectId);
        return;
      }
      target = target.parentElement;
    }
  }, []);

  const handleMouseOut = useCallback((e: React.MouseEvent) => {
    // Check if we're leaving a data-object-id element
    let target = e.target as HTMLElement | null;
    while (target && target !== e.currentTarget) {
      const objectId = target.getAttribute('data-object-id');
      if (objectId) {
        // Only clear if the relatedTarget is not within the same object
        let related = e.relatedTarget as HTMLElement | null;
        while (related && related !== e.currentTarget) {
          if (related.getAttribute('data-object-id') === objectId) {
            return; // Still within the same object
          }
          related = related.parentElement;
        }
        setHoveredObjectId((prev) => (prev === objectId ? null : prev));
        return;
      }
      target = target.parentElement;
    }
  }, []);

  const canvasObjectsArray = Array.from(canvasObjects.values()).sort((a, b) => a.zIndex - b.zIndex);
  const lineObjects = canvasObjectsArray.filter((obj) => obj.objectType === 'line');
  const nonLineObjects = canvasObjectsArray.filter((obj) => obj.objectType !== 'line');

  // Show resize handles only when exactly one object is selected
  const selectedObject = selectedObjectIds.size === 1
    ? canvasObjects.get([...selectedObjectIds][0]) ?? null
    : null;

  return (
    <div
      onMouseOver={handleMouseOver}
      onMouseOut={handleMouseOut}
      style={{
        position: 'absolute',
        inset: 0,
        pointerEvents: 'none',
      }}
    >
      {/* Invisible hover-trigger zones at anchor positions for all non-line, non-locked objects.
          These extend the hover detection area so anchors appear when approaching from outside. */}
      {activeTool === 'pointer' && nonLineObjects.map((obj) => {
        if (obj.locked) return null;
        const objBounds = getObjectBounds(obj);
        const anchors = getAnchorPoints(objBounds);
        const smallerSide = Math.min(objBounds.width, objBounds.height);
        const zoneSize = Math.max(4, Math.min(24, smallerSide * 0.2));
        return ANCHOR_POSITIONS_LIST.map((pos) => {
          const point = anchors[pos];
          return (
            <div
              key={`hover-zone-${obj.id}-${pos}`}
              data-object-id={obj.id}
              style={{
                position: 'absolute',
                left: 0,
                top: 0,
                transform: `translate(${point.x - zoneSize / 2}px, ${point.y - zoneSize / 2}px)`,
                width: zoneSize,
                height: zoneSize,
                pointerEvents: 'auto',
                borderRadius: '50%',
              }}
            />
          );
        });
      })}

      {/* Canvas objects: architecture blocks and geometric objects (DOM elements) */}
      {nonLineObjects.map((obj) => {
        const isSelected = selectedObjectIds.has(obj.id);
        if (obj.objectType === 'architecture-block') {
          if (obj.presentation === 'container' && (obj.serviceType === 'vpc' || obj.serviceType === 'subnet')) {
            return <SemanticContainerComponent key={obj.id} object={obj} isSelected={isSelected} />;
          }
          return (
            <ArchitectureBlockComponent
              key={obj.id}
              block={obj}
              isSelected={isSelected}
            />
          );
        }
        if (obj.objectType === 'semantic-container') {
          return (
            <SemanticContainerComponent key={obj.id} object={obj} isSelected={isSelected} />
          );
        }
        if (obj.objectType === 'geometric') {
          return (
            <GeometricObjectComponent
              key={obj.id}
              object={obj}
              isSelected={isSelected}
            />
          );
        }
        if (obj.objectType === 'text') {
          return (
            <TextObjectComponent
              key={obj.id}
              object={obj}
              isSelected={isSelected}
            />
          );
        }
        if (obj.objectType === 'uml') {
          return (
            <UMLObjectComponent
              key={obj.id}
              object={obj}
              isSelected={isSelected}
            />
          );
        }
        return null;
      })}

      {/* Anchor indicators on hovered non-line objects (pointer tool only, not locked) */}
      {activeTool === 'pointer' && hoveredObjectId && (() => {
        const hoveredObj = canvasObjects.get(hoveredObjectId);
        if (hoveredObj && hoveredObj.objectType !== 'line' && !hoveredObj.locked) {
          return (
            <AnchorIndicators
              objectId={hoveredObj.id}
              bounds={getObjectBounds(hoveredObj)}
              locked={hoveredObj.locked}
            />
          );
        }
        return null;
      })()}

      {/* SVG overlay layer for line objects */}
      {lineObjects.length > 0 && (
        <svg
          data-testid="line-svg-overlay"
          style={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            pointerEvents: 'none',
            overflow: 'visible',
          }}
        >
          {lineObjects.map((obj) => {
            if (obj.objectType !== 'line') return null;
            return (
              <LineObjectComponent
                key={obj.id}
                line={obj}
                isSelected={selectedObjectIds.has(obj.id)}
                onAlignmentGuidesChange={lineGuidesCallback}
              />
            );
          })}
        </svg>
      )}

      {/* Alignment guides for line objects (rendered outside SVG overlay) */}
      {lineAlignmentGuides.length > 0 && <AlignmentGuides guides={lineAlignmentGuides} />}

      {/* Resize handles on the selected canvas object */}
      {selectedObject && <ResizeHandles object={selectedObject} />}

      {/* Group bounding boxes for selected groups */}
      {(() => {
        const selectedGroupIds = new Set<string>();
        for (const id of selectedObjectIds) {
          const obj = canvasObjects.get(id);
          if (obj?.groupId && objectGroups.has(obj.groupId)) {
            selectedGroupIds.add(obj.groupId);
          }
        }
        return Array.from(selectedGroupIds).map((gid) => (
          <GroupBoundingBox key={gid} groupId={gid} />
        ));
      })()}
    </div>
  );
}
