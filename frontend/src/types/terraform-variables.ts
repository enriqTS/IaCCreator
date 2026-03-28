/**
 * Terraform variable schemas and global configuration types.
 * Defines per-service variable schemas and project-level Terraform config.
 *
 * These types mirror the backend Pydantic models in variable_schemas.py exactly.
 */

export type TerraformVariableType = 'string' | 'number' | 'bool' | 'map' | 'list';

export interface ValidationRule {
  min?: number | null;
  max?: number | null;
  pattern?: string | null;
  pattern_description?: string | null;
  allowed_values?: (string | number | boolean)[] | null;
}

export interface OptionEntry {
  value: string | number | boolean;
  label: string;
  group?: string | null;
}

export interface VisibleWhen {
  field: string;
  equals: string | number | boolean;
}

export interface TerraformVariableSchema {
  name: string;
  type: TerraformVariableType;
  description: string;
  default?: string | number | boolean | null;
  group?: string;
  options?: OptionEntry[] | null;
  validation?: ValidationRule | null;
  visible_when?: VisibleWhen | null;
}

export type ServiceVariableSchemas = Record<string, TerraformVariableSchema[]>;

export interface GlobalTerraformConfig {
  backend: {
    type: string;
    config: Record<string, string>;
  };
  provider: {
    region: string;
    profile?: string;
  };
  versionConstraints: {
    terraformVersion?: string;
    awsProviderVersion?: string;
  };
  environments: { name: string; variableOverrides: Record<string, string> }[];
  globalVariables: {
    name: string;
    type: TerraformVariableType;
    description: string;
    default?: string;
  }[];
}

export const DEFAULT_GLOBAL_CONFIG: GlobalTerraformConfig = {
  backend: { type: 'local', config: {} },
  provider: { region: 'us-east-1' },
  versionConstraints: {},
  environments: [],
  globalVariables: [],
};

import { BUNDLED_SCHEMAS } from '@/data/bundled-schemas';

/**
 * Returns a Record of variable names to their default values for a given service type.
 * Variables with a default use that value; string variables default to '',
 * number variables default to 0, and bool variables default to false.
 */
export function getDefaultVariables(serviceType: string): Record<string, string | number | boolean> {
  const schemas = BUNDLED_SCHEMAS[serviceType];
  if (!schemas) return {};

  const defaults: Record<string, string | number | boolean> = {};
  for (const schema of schemas) {
    if (schema.default !== undefined && schema.default !== null) {
      defaults[schema.name] = schema.default;
    } else {
      switch (schema.type) {
        case 'string':
          defaults[schema.name] = '';
          break;
        case 'number':
          defaults[schema.name] = 0;
          break;
        case 'bool':
          defaults[schema.name] = false;
          break;
        // map and list types don't get simple defaults here
      }
    }
  }
  return defaults;
}
