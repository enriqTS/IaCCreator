'use client';

import type { ArchitectureBlock } from '@/types/diagram';
import { VARIABLE_SCHEMAS } from '@/types/terraform-variables';
import { useDiagramStore } from '@/store/diagram-store';

interface VariablesPanelProps {
  block: ArchitectureBlock;
}

/** Renders editable Terraform variable fields for the selected architecture block. */
export default function VariablesPanel({ block }: VariablesPanelProps) {
  const setTerraformVariable = useDiagramStore((s) => s.setTerraformVariable);
  const schemas = VARIABLE_SCHEMAS[block.serviceType];

  if (!schemas || schemas.length === 0) {
    return (
      <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '13px' }}>
        No variables defined for this service type.
      </p>
    );
  }

  return (
    <div
      data-testid="variables-panel"
      style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'flex-end' }}
    >
      {schemas.map((schema) => {
        const currentValue = block.terraformVariables[schema.name];
        const hasDefault = schema.default !== undefined;
        const isRequired = !hasDefault && !schema.optional;
        const isEmpty =
          currentValue === undefined ||
          currentValue === '' ||
          (schema.tfType === 'number' && currentValue === 0 && !hasDefault);
        const showValidation = isRequired && isEmpty;

        if (schema.tfType === 'bool') {
          return (
            <label
              key={schema.name}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '13px',
                paddingBottom: '2px',
              }}
              title={schema.description}
            >
              <input
                data-testid={`var-${schema.name}`}
                type="checkbox"
                checked={typeof currentValue === 'boolean' ? currentValue : !!schema.default}
                onChange={(e) =>
                  setTerraformVariable(block.id, schema.name, e.target.checked)
                }
              />
              <span style={{ color: 'rgba(255,255,255,0.6)' }}>{schema.name}</span>
            </label>
          );
        }

        if (schema.tfType === 'number') {
          return (
            <label
              key={schema.name}
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
                fontSize: '13px',
              }}
              title={schema.description}
            >
              <span style={{ color: 'rgba(255,255,255,0.6)' }}>
                {schema.name}
                {showValidation && (
                  <span data-testid={`validation-${schema.name}`} style={{ color: '#ef4444', marginLeft: '4px' }}>*</span>
                )}
              </span>
              <input
                data-testid={`var-${schema.name}`}
                type="number"
                value={typeof currentValue === 'number' ? currentValue : ''}
                onChange={(e) => {
                  const val = e.target.value === '' ? 0 : Number(e.target.value);
                  setTerraformVariable(block.id, schema.name, val);
                }}
                placeholder={hasDefault ? String(schema.default) : undefined}
                style={{
                  ...inputStyle,
                  ...(showValidation ? validationBorderStyle : {}),
                }}
              />
            </label>
          );
        }

        // Default: string type
        return (
          <label
            key={schema.name}
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '4px',
              fontSize: '13px',
            }}
            title={schema.description}
          >
            <span style={{ color: 'rgba(255,255,255,0.6)' }}>
              {schema.name}
              {showValidation && (
                <span data-testid={`validation-${schema.name}`} style={{ color: '#ef4444', marginLeft: '4px' }}>*</span>
              )}
            </span>
            <input
              data-testid={`var-${schema.name}`}
              type="text"
              value={typeof currentValue === 'string' ? currentValue : ''}
              onChange={(e) =>
                setTerraformVariable(block.id, schema.name, e.target.value)
              }
              placeholder={hasDefault ? String(schema.default) : undefined}
              style={{
                ...inputStyle,
                ...(showValidation ? validationBorderStyle : {}),
              }}
            />
          </label>
        );
      })}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  backgroundColor: '#2a2a2a',
  color: '#fff',
  border: '1px solid rgba(255,255,255,0.2)',
  borderRadius: '4px',
  padding: '4px 8px',
  fontSize: '13px',
  width: '140px',
};

const validationBorderStyle: React.CSSProperties = {
  borderColor: '#ef4444',
};
