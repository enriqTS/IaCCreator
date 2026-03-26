'use client';

import { useDiagramStore } from '@/store/diagram-store';
import DiagramElementComponent from './DiagramElement';

export default function ElementLayer() {
  const elements = useDiagramStore((s) => s.elements);

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        pointerEvents: 'none',
      }}
    >
      {Array.from(elements.values()).map((element) => (
        <DiagramElementComponent key={element.id} element={element} />
      ))}
    </div>
  );
}
