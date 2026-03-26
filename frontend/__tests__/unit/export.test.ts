import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { exportToTerraform, type ExportResult } from '@/utils/export';
import type { DiagramElement } from '@/types/diagram';
import type { ArchitectureDescription } from '@/types/serialization';

function makeElement(overrides: Partial<DiagramElement> = {}): DiagramElement {
  return {
    id: 'el-1',
    serviceType: 'lambda',
    name: 'lambda-1',
    position: { x: 0, y: 0 },
    config: {},
    ...overrides,
  };
}

function makeDynamoElement(hashKey = ''): DiagramElement {
  return makeElement({
    id: 'dynamo-1',
    serviceType: 'dynamodb',
    name: 'dynamodb-1',
    config: { hash_key: hashKey },
  });
}

const dummyPayload: ArchitectureDescription = {
  project_name: 'test',
  environments: [],
  resources: [],
  connections: [],
};

function serializeFn(): ArchitectureDescription {
  return dummyPayload;
}

describe('exportToTerraform', () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  // --- Empty diagram ---

  it('rejects empty diagrams', async () => {
    const elements = new Map<string, DiagramElement>();
    const result = await exportToTerraform(serializeFn, elements);
    expect(result.success).toBe(false);
    expect(result.error).toBe('No elements in diagram');
  });

  // --- Validation: DynamoDB hash_key required ---

  it('rejects DynamoDB element with empty hash_key', async () => {
    const elements = new Map<string, DiagramElement>();
    elements.set('dynamo-1', makeDynamoElement(''));
    const result = await exportToTerraform(serializeFn, elements);
    expect(result.success).toBe(false);
    expect(result.fieldErrors).toBeDefined();
    expect(result.fieldErrors!['dynamodb-1.hash_key']).toContain('hash_key');
  });

  it('rejects DynamoDB element with undefined hash_key', async () => {
    const el = makeElement({
      id: 'dynamo-1',
      serviceType: 'dynamodb',
      name: 'dynamodb-1',
      config: {},
    });
    const elements = new Map<string, DiagramElement>();
    elements.set('dynamo-1', el);
    const result = await exportToTerraform(serializeFn, elements);
    expect(result.success).toBe(false);
    expect(result.fieldErrors).toBeDefined();
  });

  it('passes validation for DynamoDB with non-empty hash_key', async () => {
    const elements = new Map<string, DiagramElement>();
    elements.set('dynamo-1', makeDynamoElement('pk'));

    const blob = new Blob(['zipdata'], { type: 'application/zip' });
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      blob: () => Promise.resolve(blob),
    });

    // Mock DOM methods for download trigger
    const createElementSpy = vi.spyOn(document, 'createElement').mockReturnValue({
      href: '',
      download: '',
      click: vi.fn(),
    } as unknown as HTMLAnchorElement);
    vi.spyOn(document.body, 'appendChild').mockImplementation((node) => node);
    vi.spyOn(document.body, 'removeChild').mockImplementation((node) => node);
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:fake');
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});

    const result = await exportToTerraform(serializeFn, elements);
    expect(result.success).toBe(true);

    createElementSpy.mockRestore();
  });

  // --- Lambda has no required fields ---

  it('passes validation for Lambda with empty config', async () => {
    const elements = new Map<string, DiagramElement>();
    elements.set('el-1', makeElement());

    const blob = new Blob(['zipdata'], { type: 'application/zip' });
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      blob: () => Promise.resolve(blob),
    });

    vi.spyOn(document, 'createElement').mockReturnValue({
      href: '',
      download: '',
      click: vi.fn(),
    } as unknown as HTMLAnchorElement);
    vi.spyOn(document.body, 'appendChild').mockImplementation((node) => node);
    vi.spyOn(document.body, 'removeChild').mockImplementation((node) => node);
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:fake');
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});

    const result = await exportToTerraform(serializeFn, elements);
    expect(result.success).toBe(true);
  });

  // --- Successful export (200) ---

  it('triggers download on successful 200 response', async () => {
    const elements = new Map<string, DiagramElement>();
    elements.set('el-1', makeElement());

    const blob = new Blob(['zipdata'], { type: 'application/zip' });
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      blob: () => Promise.resolve(blob),
    });

    const clickFn = vi.fn();
    vi.spyOn(document, 'createElement').mockReturnValue({
      href: '',
      download: '',
      click: clickFn,
    } as unknown as HTMLAnchorElement);
    vi.spyOn(document.body, 'appendChild').mockImplementation((node) => node);
    vi.spyOn(document.body, 'removeChild').mockImplementation((node) => node);
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:fake');
    const revokeSpy = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});

    const result = await exportToTerraform(serializeFn, elements);
    expect(result.success).toBe(true);
    expect(clickFn).toHaveBeenCalled();
    expect(revokeSpy).toHaveBeenCalledWith('blob:fake');
  });

  it('sends correct Content-Type and payload', async () => {
    const elements = new Map<string, DiagramElement>();
    elements.set('el-1', makeElement());

    const blob = new Blob(['zipdata'], { type: 'application/zip' });
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      blob: () => Promise.resolve(blob),
    });
    globalThis.fetch = fetchMock;

    vi.spyOn(document, 'createElement').mockReturnValue({
      href: '',
      download: '',
      click: vi.fn(),
    } as unknown as HTMLAnchorElement);
    vi.spyOn(document.body, 'appendChild').mockImplementation((node) => node);
    vi.spyOn(document.body, 'removeChild').mockImplementation((node) => node);
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:fake');
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});

    await exportToTerraform(serializeFn, elements);

    expect(fetchMock).toHaveBeenCalledWith('/generate/zip', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(dummyPayload),
    });
  });

  // --- 422 validation errors ---

  it('parses 422 response with detail array', async () => {
    const elements = new Map<string, DiagramElement>();
    elements.set('el-1', makeElement());

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: () =>
        Promise.resolve({
          detail: [
            { loc: ['body', 'resources', 0, 'config'], msg: 'field required' },
          ],
        }),
    });

    const result = await exportToTerraform(serializeFn, elements);
    expect(result.success).toBe(false);
    expect(result.error).toBe('Validation error from server');
    expect(result.fieldErrors).toBeDefined();
    expect(result.fieldErrors!['body.resources.0.config']).toBe('field required');
  });

  it('parses 422 response with detail string', async () => {
    const elements = new Map<string, DiagramElement>();
    elements.set('el-1', makeElement());

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: () => Promise.resolve({ detail: 'Invalid input' }),
    });

    const result = await exportToTerraform(serializeFn, elements);
    expect(result.success).toBe(false);
    expect(result.fieldErrors).toBeDefined();
    expect(result.fieldErrors!['detail']).toBe('Invalid input');
  });

  // --- 500 server errors ---

  it('returns server error detail on 500', async () => {
    const elements = new Map<string, DiagramElement>();
    elements.set('el-1', makeElement());

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ detail: 'Generation failed: boom' }),
    });

    const result = await exportToTerraform(serializeFn, elements);
    expect(result.success).toBe(false);
    expect(result.error).toBe('Generation failed: boom');
  });

  it('returns generic error when 500 body is not JSON', async () => {
    const elements = new Map<string, DiagramElement>();
    elements.set('el-1', makeElement());

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.reject(new Error('not json')),
    });

    const result = await exportToTerraform(serializeFn, elements);
    expect(result.success).toBe(false);
    expect(result.error).toBe('Server error (500)');
  });

  // --- Network errors ---

  it('returns network error on fetch failure', async () => {
    const elements = new Map<string, DiagramElement>();
    elements.set('el-1', makeElement());

    globalThis.fetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'));

    const result = await exportToTerraform(serializeFn, elements);
    expect(result.success).toBe(false);
    expect(result.error).toContain('Network error');
  });
});
