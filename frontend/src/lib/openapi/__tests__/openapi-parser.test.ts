import { describe, it, expect } from 'vitest';
import { parseOpenApiSpec } from '../openapi-parser';

describe('parseOpenApiSpec', () => {
  it('parses a valid JSON OpenAPI 3.0.3 document', () => {
    const content = JSON.stringify({
      openapi: '3.0.3',
      info: { title: 'Test API', version: '1.0.0' },
      paths: { '/users': { get: { responses: { '200': { description: 'OK' } } } } },
    });

    const result = parseOpenApiSpec(content);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.spec.openapi).toBe('3.0.3');
      expect(result.spec.info.title).toBe('Test API');
      expect(result.spec.paths['/users']).toBeDefined();
    }
  });

  it('parses a valid YAML OpenAPI 3.0.3 document', () => {
    const content = `
openapi: "3.0.3"
info:
  title: YAML API
  version: "1.0.0"
paths:
  /items:
    get:
      responses:
        "200":
          description: OK
`;

    const result = parseOpenApiSpec(content);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.spec.openapi).toBe('3.0.3');
      expect(result.spec.info.title).toBe('YAML API');
      expect(result.spec.paths['/items']).toBeDefined();
    }
  });

  it('returns error for invalid JSON/YAML content', () => {
    const content = '{{{{not valid json or yaml!!!!';

    const result = parseOpenApiSpec(content);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error).toContain('Invalid format');
    }
  });

  it('returns error when openapi field is missing', () => {
    const content = JSON.stringify({
      info: { title: 'No Version', version: '1.0.0' },
      paths: {},
    });

    const result = parseOpenApiSpec(content);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error).toContain('openapi');
    }
  });

  it('returns error when info object is missing', () => {
    const content = JSON.stringify({
      openapi: '3.0.3',
      paths: {},
    });

    const result = parseOpenApiSpec(content);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error).toContain('info');
    }
  });

  it('parses a valid OpenAPI 3.1.x document', () => {
    const content = JSON.stringify({
      openapi: '3.1.0',
      info: { title: 'v3.1 API', version: '2.0.0' },
      paths: { '/health': { get: { responses: { '200': { description: 'OK' } } } } },
    });

    const result = parseOpenApiSpec(content);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.spec.openapi).toBe('3.1.0');
    }
  });

  it('returns error for OpenAPI version 2.0 (Swagger)', () => {
    const content = JSON.stringify({
      openapi: '2.0',
      info: { title: 'Old Swagger', version: '1.0.0' },
      paths: {},
    });

    const result = parseOpenApiSpec(content);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error).toContain('openapi');
    }
  });
});
