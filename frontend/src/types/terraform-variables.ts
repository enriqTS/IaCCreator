/**
 * Terraform variable schemas and global configuration types.
 * Defines per-service variable schemas and project-level Terraform config.
 */

export type TerraformVariableType = 'string' | 'number' | 'bool';

export interface TerraformVariableSchema {
  name: string;
  tfType: TerraformVariableType;
  description: string;
  default?: string | number | boolean;
  optional?: boolean;
}

export type ServiceVariableSchemas = Record<string, TerraformVariableSchema[]>;

export const VARIABLE_SCHEMAS: ServiceVariableSchemas = {
  lambda: [
    { name: 'function_name', tfType: 'string', description: 'Name of the Lambda function' },
    { name: 'handler', tfType: 'string', description: 'Lambda function handler' },
    { name: 'runtime', tfType: 'string', description: 'Lambda function runtime' },
    { name: 'memory_size', tfType: 'number', description: 'Memory size in MB', default: 128 },
    { name: 'timeout', tfType: 'number', description: 'Timeout in seconds', default: 3 },
  ],
  s3: [
    { name: 'bucket_name', tfType: 'string', description: 'Name of the S3 bucket' },
    { name: 'versioning_enabled', tfType: 'bool', description: 'Enable versioning', default: false },
  ],
  dynamodb: [
    { name: 'table_name', tfType: 'string', description: 'Name of the DynamoDB table' },
    { name: 'billing_mode', tfType: 'string', description: 'Billing mode', default: 'PAY_PER_REQUEST' },
    { name: 'hash_key', tfType: 'string', description: 'Hash key attribute name' },
    { name: 'hash_key_type', tfType: 'string', description: 'Hash key attribute type', default: 'S' },
    { name: 'range_key', tfType: 'string', description: 'Range key attribute name', optional: true },
    { name: 'range_key_type', tfType: 'string', description: 'Range key attribute type', default: 'S', optional: true },
  ],
  'api-gateway': [
    { name: 'api_name', tfType: 'string', description: 'Name of the API Gateway' },
    { name: 'protocol_type', tfType: 'string', description: 'Protocol type', default: 'HTTP' },
  ],
  cloudwatch: [
    { name: 'log_group_name', tfType: 'string', description: 'Name of the CloudWatch log group' },
    { name: 'retention_in_days', tfType: 'number', description: 'Log retention in days', default: 30 },
  ],
};

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

/**
 * Returns a Record of variable names to their default values for a given service type.
 * Variables with a default use that value; string variables default to '',
 * number variables default to 0, and bool variables default to false.
 */
export function getDefaultVariables(serviceType: string): Record<string, string | number | boolean> {
  const schemas = VARIABLE_SCHEMAS[serviceType];
  if (!schemas) return {};

  const defaults: Record<string, string | number | boolean> = {};
  for (const schema of schemas) {
    if (schema.default !== undefined) {
      defaults[schema.name] = schema.default;
    } else {
      switch (schema.tfType) {
        case 'string':
          defaults[schema.name] = '';
          break;
        case 'number':
          defaults[schema.name] = 0;
          break;
        case 'bool':
          defaults[schema.name] = false;
          break;
      }
    }
  }
  return defaults;
}
