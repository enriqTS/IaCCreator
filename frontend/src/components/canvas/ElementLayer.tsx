'use client';

import { useDiagramStore } from '@/store/diagram-store';
import DiagramElementComponent from './DiagramElement';
import ArchitectureBlockComponent from './ArchitectureBlockComponent';
import LineObjectComponent from './LineObjectComponent';
import GeometricObjectComponent from './GeometricObjectComponent';
import ResizeHandles from './ResizeHandles';

export default function ElementLayer() {
  const elements = useDiagramStore((s) => s.elements);
  const canvasObjects = useDiagramStore((s) => s.canvasObjects);
  const selectedObjectId = useDiagramStore((s) => s.selectedObjectId);

  const canvasObjectsArray = Array.from(canvasObjects.values());
  const lineObjects = canvasObjectsArray.filter((obj) => obj.objectType === 'line');
  const nonLineObjects = canvasObjectsArray.filter((obj) => obj.objectType !== 'line');

  const selectedObject = selectedObjectId ? canvasObjects.get(selectedObjectId) ?? null : null;

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        pointerEvents: 'none',
      }}
    >
      {/* Backward-compatible: existing DiagramElement rendering */}
      {Array.from(elements.values()).map((element) => (
        <DiagramElementComponent key={element.id} element={element} />
      ))}

      {/* Canvas objects: architecture blocks and geometric objects (DOM elements) */}
      {nonLineObjects.map((obj) => {
        const isSelected = obj.id === selectedObjectId;
        if (obj.objectType === 'architecture-block') {
          return (
            <ArchitectureBlockComponent
              key={obj.id}
              block={obj}
              isSelected={isSelected}
            />
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
        return null;
      })}

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
                isSelected={obj.id === selectedObjectId}
              />
            );
          })}
        </svg>
      )}

      {/* Resize handles on the selected canvas object */}
      {selectedObject && <ResizeHandles object={selectedObject} />}
    </div>
  );
}
