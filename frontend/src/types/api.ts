export interface DiagramSummary {
  diagram_id: string;
  project_name: string;
  updated_at: string;
}

export interface ApiError {
  type: 'network' | 'http';
  status?: number;
  message: string;
  fieldErrors?: Record<string, string>;
}

export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: ApiError };
