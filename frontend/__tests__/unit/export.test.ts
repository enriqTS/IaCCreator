import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { DiagramState } from '@/types/serialization';
import { exportToTerraform } from '@/utils/export';

vi.mock('@/utils/api-client', () => ({
  apiClient: { generateTerraform: vi.fn() },
}));

import { apiClient } from '@/utils/api-client';

const diagram: DiagramState = {
  version: 3,
  projectName: 'test',
  environments: [],
  canvasObjects: [],
  connectors: [],
  viewport: { offsetX: 0, offsetY: 0, scale: 1 },
};
const generate = vi.mocked(apiClient.generateTerraform);

function mockDownload(): void {
  vi.spyOn(document, 'createElement').mockReturnValue({
    href: '', download: '', click: vi.fn(),
  } as unknown as HTMLAnchorElement);
  vi.spyOn(document.body, 'appendChild').mockImplementation((node) => node);
  vi.spyOn(document.body, 'removeChild').mockImplementation((node) => node);
  vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:fake');
  vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
}

describe('exportToTerraform', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('submits canonical diagram state without frontend domain validation', async () => {
    generate.mockResolvedValue({ ok: true, data: new Blob(['zip']) });
    mockDownload();
    expect(await exportToTerraform(() => diagram)).toEqual({ success: true });
    expect(generate).toHaveBeenCalledWith(diagram);
  });

  it('returns structured backend validation errors', async () => {
    generate.mockResolvedValue({
      ok: false,
      error: {
        type: 'http', status: 422, message: 'Validation error',
        fieldErrors: { 'body.canvasObjects.0.config': 'Field required' },
      },
    });
    const result = await exportToTerraform(() => diagram);
    expect(result.error).toBe('Validation error from server');
    expect(result.fieldErrors?.['body.canvasObjects.0.config']).toBe('Field required');
  });

  it('returns a default field error for unstructured 422 responses', async () => {
    generate.mockResolvedValue({
      ok: false,
      error: { type: 'http', status: 422, message: 'Validation error' },
    });
    expect((await exportToTerraform(() => diagram)).fieldErrors).toEqual({ detail: 'Validation error' });
  });

  it('returns network errors', async () => {
    generate.mockResolvedValue({
      ok: false,
      error: { type: 'network', message: 'Failed to fetch' },
    });
    expect((await exportToTerraform(() => diagram)).error).toContain('Network error');
  });
});
