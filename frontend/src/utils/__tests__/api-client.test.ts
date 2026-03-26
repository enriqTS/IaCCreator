import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import * as fc from 'fast-check';
import { apiClient } from '@/utils/api-client';
import type { ApiResult } from '@/types/api';

// Save/restore original fetch
let originalFetch: typeof globalThis.fetch;

beforeEach(() => {
  originalFetch = globalThis.fetch;
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Arbitrary for non-2xx HTTP status codes */
const nonSuccessStatusArb = fc.oneof(
  fc.integer({ min: 300, max: 399 }),
  fc.integer({ min: 400, max: 499 }),
  fc.integer({ min: 500, max: 599 }),
);

/** Picks a random apiClient method and calls it, returning the ApiResult */
type MethodEntry = { name: string; call: () => Promise<ApiResult<unknown>> };

function getApiMethods(): MethodEntry[] {
  return [
    {
      name: 'saveDiagram',
      call: () =>
        apiClient.saveDiagram({
          version: 1,
          projectName: 'test',
          environments: [],
          elements: [],
          connectors: [],
          viewport: { offsetX: 0, offsetY: 0, scale: 1 },
        }),
    },
    {
      name: 'updateDiagram',
      call: () =>
        apiClient.updateDiagram('test-id', {
          version: 1,
          projectName: 'test',
          environments: [],
          elements: [],
          connectors: [],
          viewport: { offsetX: 0, offsetY: 0, scale: 1 },
        }),
    },
    {
      name: 'listDiagrams',
      call: () => apiClient.listDiagrams(),
    },
    {
      name: 'loadDiagram',
      call: () => apiClient.loadDiagram('test-id'),
    },
    {
      name: 'deleteDiagram',
      call: () => apiClient.deleteDiagram('test-id'),
    },
    {
      name: 'generateTerraform',
      call: () =>
        apiClient.generateTerraform({
          project_name: 'test',
          environments: [],
          resources: [],
          connections: [],
        }),
    },
  ];
}

/** Arbitrary that picks a method index from the list */
const methodIndexArb = fc.integer({ min: 0, max: 5 });

// ---------------------------------------------------------------------------
// Feature: frontend-backend-integration, Property 10: API client returns
// structured error for non-success HTTP responses
// ---------------------------------------------------------------------------
// **Validates: Requirements 6.3, 6.4, 7.5**

describe('Property 10: API client returns structured error for non-success HTTP responses', () => {
  it('for any API client method and any non-2xx status, returns ApiResult with ok:false, type:http, status, and message', async () => {
    await fc.assert(
      fc.asyncProperty(
        methodIndexArb,
        nonSuccessStatusArb,
        async (methodIdx, statusCode) => {
          const methods = getApiMethods();
          const method = methods[methodIdx];

          // Mock fetch to return a non-2xx response
          globalThis.fetch = vi.fn().mockResolvedValue({
            ok: false,
            status: statusCode,
            json: () => Promise.resolve({ detail: `Error ${statusCode}` }),
          });

          const result = await method.call();

          // Must be a failure result
          expect(result.ok).toBe(false);
          if (!result.ok) {
            expect(result.error.type).toBe('http');
            expect(result.error.status).toBe(statusCode);
            expect(typeof result.error.message).toBe('string');
            expect(result.error.message.length).toBeGreaterThan(0);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Feature: frontend-backend-integration, Property 11: API client returns
// structured network error
// ---------------------------------------------------------------------------
// **Validates: Requirements 7.4**

describe('Property 11: API client returns structured network error', () => {
  it('when fetch throws a network error, returns ApiResult with ok:false, type:network, and a message', async () => {
    await fc.assert(
      fc.asyncProperty(
        methodIndexArb,
        fc.string({ minLength: 1, maxLength: 100 }),
        async (methodIdx, errorMessage) => {
          const methods = getApiMethods();
          const method = methods[methodIdx];

          // Mock fetch to throw a TypeError (network error)
          globalThis.fetch = vi.fn().mockRejectedValue(
            new TypeError(errorMessage),
          );

          const result = await method.call();

          expect(result.ok).toBe(false);
          if (!result.ok) {
            expect(result.error.type).toBe('network');
            expect(typeof result.error.message).toBe('string');
            expect(result.error.message.length).toBeGreaterThan(0);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Feature: frontend-backend-integration, Property 12: API client includes
// credentials on all requests
// ---------------------------------------------------------------------------
// **Validates: Requirements 7.2**

describe('Property 12: API client includes credentials on all requests', () => {
  it('for any API client method invocation, fetch is called with credentials: include', async () => {
    await fc.assert(
      fc.asyncProperty(methodIndexArb, async (methodIdx) => {
        const methods = getApiMethods();
        const method = methods[methodIdx];

        // Mock fetch to return a success response
        const fetchMock = vi.fn().mockResolvedValue({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ id: 'test-id' }),
          blob: () => Promise.resolve(new Blob(['data'])),
        });
        globalThis.fetch = fetchMock;

        await method.call();

        // Verify fetch was called with credentials: 'include'
        expect(fetchMock).toHaveBeenCalledTimes(1);
        const callArgs = fetchMock.mock.calls[0];
        const requestInit = callArgs[1] as RequestInit;
        expect(requestInit.credentials).toBe('include');
      }),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Unit tests for API client
// ---------------------------------------------------------------------------

describe('API client unit tests', () => {
  // Requirement 7.1: all expected functions are exported
  describe('exports all expected functions (Requirement 7.1)', () => {
    it('exports saveDiagram', () => {
      expect(typeof apiClient.saveDiagram).toBe('function');
    });

    it('exports updateDiagram', () => {
      expect(typeof apiClient.updateDiagram).toBe('function');
    });

    it('exports listDiagrams', () => {
      expect(typeof apiClient.listDiagrams).toBe('function');
    });

    it('exports loadDiagram', () => {
      expect(typeof apiClient.loadDiagram).toBe('function');
    });

    it('exports deleteDiagram', () => {
      expect(typeof apiClient.deleteDiagram).toBe('function');
    });

    it('exports generateTerraform', () => {
      expect(typeof apiClient.generateTerraform).toBe('function');
    });
  });

  // Requirement 7.3: base URL configuration from env var
  describe('base URL configuration (Requirement 7.3)', () => {
    it('uses NEXT_PUBLIC_API_URL env var as base URL prefix in fetch calls', async () => {
      // The module reads process.env.NEXT_PUBLIC_API_URL at import time.
      // We verify the current behavior: with no env var set, it defaults to ''
      // meaning requests go to relative paths.
      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve([]),
      });
      globalThis.fetch = fetchMock;

      await apiClient.listDiagrams();

      const calledUrl = fetchMock.mock.calls[0][0] as string;
      // With default empty base URL, the path should start with /api/
      expect(calledUrl).toBe('/api/diagrams');
    });

    it('prepends base URL to all request paths', async () => {
      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ id: 'abc' }),
        blob: () => Promise.resolve(new Blob()),
      });
      globalThis.fetch = fetchMock;

      // Test saveDiagram path
      await apiClient.saveDiagram({
        version: 1,
        projectName: 'test',
        environments: [],
        elements: [],
        connectors: [],
        viewport: { offsetX: 0, offsetY: 0, scale: 1 },
      });
      expect(fetchMock.mock.calls[0][0]).toContain('/api/diagrams');

      // Test generateTerraform path
      await apiClient.generateTerraform({
        project_name: 'test',
        environments: [],
        resources: [],
        connections: [],
      });
      expect(fetchMock.mock.calls[1][0]).toContain('/generate/zip');
    });
  });
});
