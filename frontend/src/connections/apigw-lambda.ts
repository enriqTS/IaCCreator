import type { ConnectionSchema } from './registry';

export const apiGatewayLambdaSchema: ConnectionSchema = {
  sourcePair: ['api-gateway', 'lambda'],
  label: 'API Gateway → Lambda',
  fields: [
    {
      key: 'connection_role',
      label: 'Role',
      type: 'radio',
      defaultValue: 'route_handler',
      options: [
        { value: 'route_handler', label: 'Route Handler' },
        { value: 'authorizer', label: 'Authorizer' },
      ],
    },
    {
      key: 'route_path',
      label: 'Route',
      type: 'linkedSelect',
      linkedConfigPath: 'routes',
      displayKey: 'path',
      createTemplate: { methods: ['ANY'], path: '', integration_name: '' },
      validation: {
        required: true,
        pattern: /^\/[\w\-/{}\$]*$/,
        maxLength: 128,
        errorMessage: 'Must start with / and contain only alphanumeric, /, -, _, {, }, $',
      },
      visibleWhen: { field: 'connection_role', value: 'route_handler' },
    },
    {
      key: 'authorizer_name',
      label: 'Authorizer Name',
      type: 'text',
      validation: {
        required: true,
        pattern: /^[\w\-]+$/,
        maxLength: 128,
        errorMessage: 'Only alphanumeric, hyphens, and underscores (1-128 chars)',
      },
      visibleWhen: { field: 'connection_role', value: 'authorizer' },
    },
    {
      key: 'payload_format_version',
      label: 'Payload Format Version',
      type: 'select',
      defaultValue: '2.0',
      options: [
        { value: '1.0', label: '1.0' },
        { value: '2.0', label: '2.0' },
      ],
      visibleWhen: { field: 'connection_role', value: 'authorizer' },
    },
  ],
  getLabel: (config) => {
    const role = config.connection_role as string;
    if (role === 'authorizer') {
      const name = config.authorizer_name || 'auth';
      return `Authorizer: ${name}`;
    }
    // route_handler connections have no label on the line - routes are shown
    // in the "connected routes" read-only list within the connection panel instead.
    // This avoids showing a single route path when multiple routes may target the same lambda.
    if (role === 'route_handler' || !role) {
      return null;
    }
    return null;
  },
  getDashed: (config) => config.connection_role === 'authorizer',
};
