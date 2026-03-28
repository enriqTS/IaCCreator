'use client';

import type { ArchitectureBlock } from '@/types/diagram';
import { VARIABLE_SCHEMAS } from '@/types/terraform-variables';
import { useDiagramStore } from '@/store/diagram-store';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';

interface VariablesPanelProps {
  block: ArchitectureBlock;
}

/** Convert snake_case variable names to human-readable labels. */
function humanizeLabel(name: string): string {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Renders editable Terraform variable fields for the selected architecture block. */
export default function VariablesPanel({ block }: VariablesPanelProps) {
  const setTerraformVariable = useDiagramStore((s) => s.setTerraformVariable);
  const schemas = VARIABLE_SCHEMAS[block.serviceType];

  if (!schemas || schemas.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No variables defined for this service type.
      </p>
    );
  }

  return (
    <div
      data-testid="variables-panel"
      className="grid grid-cols-2 gap-3"
    >
      {schemas.map((schema) => {
        const currentValue = block.terraformVariables[schema.name];
        const hasDefault = schema.default !== undefined;
        const isRequired = !hasDefault;
        const label = humanizeLabel(schema.name);

        if (schema.type === 'bool') {
          return (
            <label
              key={schema.name}
              className="flex items-center gap-2 text-sm col-span-2"
              title={schema.description}
            >
              <Checkbox
                data-testid={`var-${schema.name}`}
                checked={typeof currentValue === 'boolean' ? currentValue : !!schema.default}
                onCheckedChange={(checked) =>
                  setTerraformVariable(block.id, schema.name, !!checked)
                }
              />
              <span className="text-muted-foreground">{label}</span>
            </label>
          );
        }

        if (schema.type === 'number') {
          return (
            <div
              key={schema.name}
              className="flex flex-col gap-1.5"
              title={schema.description}
            >
              <Label className="text-xs text-muted-foreground">
                {label}
                {isRequired && (
                  <span data-testid={`required-${schema.name}`} className="text-muted-foreground/50 ml-1">*</span>
                )}
              </Label>
              <Input
                data-testid={`var-${schema.name}`}
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                value={typeof currentValue === 'number' ? String(currentValue) : ''}
                onChange={(e) => {
                  const raw = e.target.value.replace(/[^0-9]/g, '');
                  const val = raw === '' ? 0 : Number(raw);
                  setTerraformVariable(block.id, schema.name, val);
                }}
                placeholder={hasDefault ? String(schema.default) : undefined}
              />
            </div>
          );
        }

        // Default: string type
        return (
          <div
            key={schema.name}
            className="flex flex-col gap-1.5"
            title={schema.description}
          >
            <Label className="text-xs text-muted-foreground">
              {label}
              {isRequired && (
                <span data-testid={`required-${schema.name}`} className="text-muted-foreground/50 ml-1">*</span>
              )}
            </Label>
            <Input
              data-testid={`var-${schema.name}`}
              type="text"
              value={typeof currentValue === 'string' ? currentValue : ''}
              onChange={(e) =>
                setTerraformVariable(block.id, schema.name, e.target.value)
              }
              placeholder={hasDefault ? String(schema.default) : undefined}
            />
          </div>
        );
      })}
    </div>
  );
}
