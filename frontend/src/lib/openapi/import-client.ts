/**
 * Client for the backend's OpenAPI import endpoint.
 *
 * Parsing and interpretation happen server-side; this only carries text there
 * and shapes the reply for the store.
 */

import type { MapResult } from './types';

interface ApiResponse {
  routes: MapResult['routes'];
  authorizers: MapResult['authorizers'];
  settings: {
    api_name?: string | null;
    description?: string | null;
    api_key_required?: boolean | null;
    cors_configuration?: Record<string, string> | null;
    protocol_type: string;
  };
  server_urls: string[];
  summary: {
    route_count: number;
    authorizer_count: number;
    has_api_key: boolean;
    has_cors: boolean;
    protocol_type: string;
  };
}

export type ImportOutcome =
  | { success: true; result: MapResult }
  | { success: false; error: string };

/** Send a raw OpenAPI document to the backend and map the reply for the store. */
export async function importOpenApi(
  content: string,
  selectedServerUrl?: string,
): Promise<ImportOutcome> {
  let response: Response;
  try {
    response = await fetch('/api/import/openapi', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, selected_server_url: selectedServerUrl ?? null }),
    });
  } catch {
    return { success: false, error: 'Could not reach the server to import the document.' };
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    return {
      success: false,
      error: body?.detail ?? `Import failed with status ${response.status}`,
    };
  }

  const body: ApiResponse = await response.json();
  return {
    success: true,
    result: {
      routes: body.routes,
      authorizers: body.authorizers,
      settings: {
        api_name: body.settings.api_name ?? undefined,
        description: body.settings.description ?? undefined,
        api_key_required: body.settings.api_key_required ?? undefined,
        cors_configuration: body.settings.cors_configuration ?? undefined,
        protocol_type: body.settings.protocol_type as MapResult['settings']['protocol_type'],
      },
      serverUrls: body.server_urls,
      summary: {
        routeCount: body.summary.route_count,
        authorizerCount: body.summary.authorizer_count,
        hasApiKey: body.summary.has_api_key,
        hasCors: body.summary.has_cors,
        protocolType: body.summary.protocol_type as MapResult['summary']['protocolType'],
      },
    },
  };
}
