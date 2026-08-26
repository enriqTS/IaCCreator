/**
 * Terraform variable schemas and global configuration types.
 * Defines per-service variable schemas and project-level Terraform config.
 *
 * These types mirror the schema the backend serves from its per-service config models.
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
  /** Short human name for the field; the description is the long explanation. */
  label: string;
  required?: boolean;
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

export const EMPTY_GLOBAL_CONFIG: GlobalTerraformConfig = {
  backend: { type: '', config: {} },
  provider: { region: '' },
  versionConstraints: {},
  environments: [],
  globalVariables: [],
};
