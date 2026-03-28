import { fetchSchemas, getSchemas, clearSchemaCache } from '@/store/schema-store';
import { BUNDLED_SCHEMAS } from '@/data/bundled-schemas';

// Store the original fetch so we can restore it
const originalFetch = globalThis.fetch;

describe('schema-store', () => {
  beforeEach(() => {
    clearSchemaCache();
    globalThis.fetch = originalFetch;
  });

  afterAll(() => {
    globalThis.fetch = originalFetch;
  });

  it('fetches schemas from API and caches the result', async () => {
    const mockResponse: Record<string, unknown[]> = {
      lambda: [{ name: 'function_name', type: 'string', description: 'test' }],
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const result = await fetchSchemas();
    expect(result).toEqual(mockResponse);
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/variable-schemas');

    // Second call should return cached result without fetching again
    const result2 = await fetchSchemas();
    expect(result2).toEqual(mockResponse);
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });

  it('falls back to bundled schemas when fetch fails', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

    const result = await fetchSchemas();
    expect(result).toEqual(BUNDLED_SCHEMAS);
  });

  it('falls back to bundled schemas when response is not ok', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
    });

    const result = await fetchSchemas();
    expect(result).toEqual(BUNDLED_SCHEMAS);
  });

  it('getSchemas returns bundled schemas before any fetch', () => {
    const result = getSchemas();
    expect(result).toEqual(BUNDLED_SCHEMAS);
  });

  it('getSchemas returns cached schemas after successful fetch', async () => {
    const mockResponse: Record<string, unknown[]> = {
      s3: [{ name: 'bucket_name', type: 'string', description: 'test' }],
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    await fetchSchemas();
    const result = getSchemas();
    expect(result).toEqual(mockResponse);
  });

  it('clearSchemaCache resets the cache so next fetch hits API again', async () => {
    const mockResponse1 = { lambda: [{ name: 'a', type: 'string', description: 'first' }] };
    const mockResponse2 = { lambda: [{ name: 'b', type: 'string', description: 'second' }] };

    globalThis.fetch = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockResponse1) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockResponse2) });

    const first = await fetchSchemas();
    expect(first).toEqual(mockResponse1);

    clearSchemaCache();

    const second = await fetchSchemas();
    expect(second).toEqual(mockResponse2);
    expect(globalThis.fetch).toHaveBeenCalledTimes(2);
  });
});
