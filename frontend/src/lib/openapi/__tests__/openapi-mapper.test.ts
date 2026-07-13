import { describe, it, expect } from 'vitest';
import { mapOpenApiToConfig } from '../openapi-mapper';
import type { OpenApiSpec } from '../types';

function makeMinimalSpec(overrides: Partial<OpenApiSpec> = {}): OpenApiSpec {
  return {
    openapi: '3.0.3',
    info: { title: 'Test API', version: '1.0.0' },
    paths: {},
    ...overrides,
  };
}

describe('mapOpenApiToConfig', () => {
  describe('route extraction', () => {
    it('extracts routes for multiple methods on a single path', () => {
      const spec = makeMinimalSpec({
        paths: {
          '/users': {
            get: { responses: { '200': { description: 'OK' } } },
            post: { responses: { '201': { description: 'Created' } } },
          },
        },
      });

      const result = mapOpenApiToConfig(spec);
      expect(result.routes).toHaveLength(2);

      const methods = result.routes.map((r) => r.methods[0]).sort();
      expect(methods).toEqual(['GET', 'POST']);
      expect(result.routes.every((r) => r.path === '/users')).toBe(true);
    });

    it('preserves path parameters in {param} syntax', () => {
      const spec = makeMinimalSpec({
        paths: {
          '/users/{userId}/posts/{postId}': {
            get: { responses: { '200': { description: 'OK' } } },
          },
        },
      });

      const result = mapOpenApiToConfig(spec);
      expect(result.routes[0].path).toBe('/users/{userId}/posts/{postId}');
    });
  });

  describe('API metadata extraction', () => {
    it('extracts title and description from info object', () => {
      const spec = makeMinimalSpec({
        info: {
          title: 'My Cool API',
          description: 'A description of the API',
          version: '1.0.0',
        },
      });

      const result = mapOpenApiToConfig(spec);
      expect(result.settings.api_name).toBe('My Cool API');
      expect(result.settings.description).toBe('A description of the API');
    });
  });

  describe('security scheme extraction', () => {
    it('sets api_key_required when apiKey scheme is referenced globally', () => {
      const spec = makeMinimalSpec({
        paths: {
          '/data': { get: { responses: { '200': { description: 'OK' } } } },
        },
        security: [{ ApiKeyAuth: [] }],
        components: {
          securitySchemes: {
            ApiKeyAuth: {
              type: 'apiKey',
              in: 'header',
              name: 'X-API-Key',
            },
          },
        },
      });

      const result = mapOpenApiToConfig(spec);
      expect(result.settings.api_key_required).toBe(true);
      expect(result.routes[0].api_key_required).toBe(true);
    });

    it('creates JWT authorizer from oauth2 security scheme', () => {
      const spec = makeMinimalSpec({
        paths: {
          '/secure': { get: { responses: { '200': { description: 'OK' } } } },
        },
        security: [{ OAuth2: [] }],
        components: {
          securitySchemes: {
            OAuth2: {
              type: 'oauth2',
              flows: {
                authorizationCode: {
                  authorizationUrl: 'https://auth.example.com/authorize',
                  tokenUrl: 'https://auth.example.com/token',
                },
              },
            },
          },
        },
      });

      const result = mapOpenApiToConfig(spec);
      expect(result.authorizers).toHaveLength(1);
      expect(result.authorizers[0].type).toBe('JWT');
      expect(result.authorizers[0].name).toBe('OAuth2');
      expect(result.authorizers[0].issuer_url).toBe('https://auth.example.com/token');
    });

    it('applies per-operation security override', () => {
      const spec = makeMinimalSpec({
        paths: {
          '/public': {
            get: {
              security: [],
              responses: { '200': { description: 'OK' } },
            },
          },
          '/private': {
            get: {
              responses: { '200': { description: 'OK' } },
            },
          },
        },
        security: [{ ApiKeyAuth: [] }],
        components: {
          securitySchemes: {
            ApiKeyAuth: {
              type: 'apiKey',
              in: 'header',
              name: 'X-API-Key',
            },
          },
        },
      });

      const result = mapOpenApiToConfig(spec);
      const publicRoute = result.routes.find((r) => r.path === '/public');
      const privateRoute = result.routes.find((r) => r.path === '/private');

      // Public route has empty security → no auth
      expect(publicRoute?.api_key_required).toBe(false);
      // Private route inherits global security
      expect(privateRoute?.api_key_required).toBe(true);
    });

    it('treats empty security array as no auth', () => {
      const spec = makeMinimalSpec({
        paths: {
          '/open': {
            get: {
              security: [],
              responses: { '200': { description: 'OK' } },
            },
          },
        },
        security: [{ ApiKeyAuth: [] }],
        components: {
          securitySchemes: {
            ApiKeyAuth: {
              type: 'apiKey',
              in: 'header',
              name: 'X-API-Key',
            },
          },
        },
      });

      const result = mapOpenApiToConfig(spec);
      const route = result.routes[0];
      expect(route.api_key_required).toBe(false);
      expect(route.authorizer_name).toBeUndefined();
    });
  });

  describe('server URL handling', () => {
    it('applies selected server URL to target_service_uri', () => {
      const spec = makeMinimalSpec({
        paths: {
          '/items': { get: { responses: { '200': { description: 'OK' } } } },
          '/orders': { post: { responses: { '201': { description: 'Created' } } } },
        },
        servers: [
          { url: 'https://api.example.com' },
          { url: 'https://staging.example.com' },
        ],
      });

      const result = mapOpenApiToConfig(spec, {
        selectedServerUrl: 'https://api.example.com',
      });

      const itemsRoute = result.routes.find((r) => r.path === '/items');
      const ordersRoute = result.routes.find((r) => r.path === '/orders');

      expect(itemsRoute?.target_service_uri).toBe('https://api.example.com/items');
      expect(ordersRoute?.target_service_uri).toBe('https://api.example.com/orders');
      expect(result.serverUrls).toEqual([
        'https://api.example.com',
        'https://staging.example.com',
      ]);
    });
  });

  describe('tag extraction', () => {
    it('extracts first tag from operations', () => {
      const spec = makeMinimalSpec({
        paths: {
          '/pets': {
            get: {
              tags: ['Pets', 'Animals'],
              responses: { '200': { description: 'OK' } },
            },
          },
          '/users': {
            get: {
              tags: ['Users'],
              responses: { '200': { description: 'OK' } },
            },
          },
        },
      });

      const result = mapOpenApiToConfig(spec);
      const petsRoute = result.routes.find((r) => r.path === '/pets');
      const usersRoute = result.routes.find((r) => r.path === '/users');

      expect(petsRoute?.tag).toBe('Pets');
      expect(usersRoute?.tag).toBe('Users');
    });
  });
});
