'use client';

import { useDiagramStore } from '@/store/diagram-store';
import { Input } from '@/components/ui/input';
import FieldLabel from './schema/FieldLabel';

interface ObjectNameFieldProps {
  objectId: string;
  description?: string;
}

const FIELD_ID = 'config-object-name';

/** Renaming belongs with the rest of an object's configuration, not only on the canvas. */
export default function ObjectNameField({ objectId, description }: ObjectNameFieldProps) {
  const object = useDiagramStore((s) => s.canvasObjects.get(objectId));
  const updateCanvasObject = useDiagramStore((s) => s.updateCanvasObject);

  if (!object) return null;

  return (
    <div className="flex flex-col gap-1.5">
      <FieldLabel label="Name" description={description} required htmlFor={FIELD_ID} />
      <Input
        id={FIELD_ID}
        data-testid="object-name-field"
        type="text"
        value={object.name}
        onChange={(e) => updateCanvasObject(objectId, { name: e.target.value })}
      />
    </div>
  );
}
