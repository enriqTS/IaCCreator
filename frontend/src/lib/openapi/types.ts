/**
 * Type definitions for OpenAPI specification import.
 *
 * The document itself is parsed and interpreted by the backend; these describe
 * the shape it returns for the APIGW Config Store.
 */

import type { RouteItem, AuthorizerItem, ProtocolType } from '@/types/apigw-config';

/** How an import combines with whatever the block already has. */
export type ImportStrategy = 'replace' | 'merge';

export interface MapResult {
  /** Extracted route items with optional tag metadata. */
  routes: Array<RouteItem>;
  /** Extracted authorizer items from security schemes. */
  authorizers: Array<AuthorizerItem>;
  /** Extracted API settings. */
  settings: {
    api_name?: string;
    description?: string;
    api_key_required?: boolean;
    cors_configuration?: Record<string, string>;
    protocol_type: ProtocolType;
  };
  /** Server URLs extracted from the spec. */
  serverUrls: string[];
  /** Summary of the import for preview display. */
  summary: {
    routeCount: number;
    authorizerCount: number;
    hasApiKey: boolean;
    hasCors: boolean;
    protocolType: ProtocolType;
  };
}