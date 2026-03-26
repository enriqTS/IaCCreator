import { describe, it, expect, vi, beforeEach } from 'vitest';
import { exportToTerraform, type ExportResult } from '@/utils/export';
import type { DiagramElement } from '@/types/diagram';
import type { ArchitectureDescription } from '@/types/serialization';

// Mock the apiClient module
vi.mock('@/utils/api-client', () => ({
  apiClient: {
    generateTerraform: vi.fn(),
  },
}));

import { apiClient } from '@/utils/api-client';

const mockGenerateTerraform = vi.mocked(apiClient.generateTerraform);

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
  beforeEach(() => {
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
    mockGenerateTerraform.mockResolvedValue({ ok: true, data: blob });

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

  // --- Lambda has no required fields ---

  it('passes validation for Lambda with empty config', async () => {
    const elements = new Map<string, DiagramElement>();
    elements.set('el-1', makeElement());

    const blob = new Blob(['zipdata'], { type: 'application/zip' });
    mockGenerateTerraform.mockResolvedValue({ ok: true, data: blob });

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

  it('triggers download on successful response', async () => {
    const elements = new Map<string, DiagramElement>();
    elements.set('el-1', makeElement());

    const blob = new Blob(['zipdata'], { type: 'application/zip' });
    mockGenerateTerraform.mockResolvedValue({ ok: true, data: blob });

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

  it('calls apiClient.generateTerraform with the serialized payload', async () => {
    const elements = new Map<string, DiagramElement>();
    elements.set('el-1', makeElement());

    const blob = new Blob(['zipdata'], { type: 'application/zip' });
    mockGenerateTerraform.mockResolvedValue({ ok: true, data: blob });

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

    expect(mockGenerateTerraform).toHaveBeenCalledWith(dummyPayload);
  });

  // --- 422 validation errors ---

  it('maps 422 error with fieldErrors from apiClient', async () => {
    const elements = new Map<string, DiagramElement>();
    elements.set('el-1', makeElement());

    mockGenerateTerraform.mockResolvedValue({
      ok: false,
      error: {
        type: 'http',
        status: 422,
        message: 'Validation error',
        fieldErrors: { 'body.resources.0.config': 'field required' },
      },
    });

    const result = await exportToTerraform(serializeFn, elements);
    expect(result.success).toBe(false);
    expect(result.error).toBe('Validation error from server');
    expect(result.fieldErrors).toBeDefined();
    expect(result.fieldErrors!['body.resources.0.config']).toBe('field required');
  });

  it('maps 422 error without fieldErrors to default', async () => {
    const elements = new Map<string, DiagramElement>();
    elements.set('el-1', makeElement());

    mockGenerateTerraform.mockResolvedValue({
      ok: false,
      error: {
        type: 'http',
        status: 422,
        message: 'Validation error',
      },
    });

    const result = await exportToTerraform(serializeFn, elements);
    expect(result.success).toBe(false);
    expect(result.fieldErrors).toBeDefined();
    expect(result.fieldErrors!['detail']).toBe('Validation error');
  });

  // --- 500 server errors ---

  it('returns server error detail on 500', async () => {
    const elements = new Map<string, DiagramElement>();
    elements.set('el-1', makeElement());

    mockGenerateTerraform.mockResolvedValue({
      ok: false,
      error: {
        type: 'http',
        status: 500,
        message: 'Generation failed: boom',
      },
    });

    const result = await exportToTerraform(serializeFn, elements);
    expect(result.success).toBe(false);
    expect(result.error).toBe('Generation failed: boom');
  });

  it('returns generic HTTP message for non-422 errors', async () => {
    const elements = new Map<string, DiagramElement>();
    elements.set('el-1', makeElement());

    mockGenerateTerraform.mockResolvedValue({
      ok: false,
      error: {
        type: 'http',
        status: 500,
        message: 'HTTP 500',
      },
    });

    const result = await exportToTerraform(serializeFn, elements);
    expect(result.success).toBe(false);
    expect(result.error).toBe('HTTP 500');
  });

  // --- Network errors ---

  it('returns network error on apiClient network failure', async () => {
    const elements = new Map<string, DiagramElement>();
    elements.set('el-1', makeElement());

    mockGenerateTerraform.mockResolvedValue({
      ok: false,
      error: {
        type: 'network',
        message: 'Failed to fetch',
      },
    });

    const result = await exportToTerraform(serializeFn, elements);
    expect(result.success).toBe(false);
    expect(result.error).toContain('Network error');
  });
});
