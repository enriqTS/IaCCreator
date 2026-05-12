/**
 * Type definitions for OpenAPI specification import.
 *
 * These types represent the subset of OpenAPI 3.0.x/3.1.x structures
 * needed for parsing and mapping specs into APIGW Config Store entities.
 */

import type { RouteItem, AuthorizerItem, ProtocolType } from '@/types/apigw-config';

/**
 * Minimal typed representation of an OpenAPI 3.x document.
 * Only includes fields relevant to API Gateway configuration extraction.
 */
export interface OpenApiSpec {
  /** OpenAPI version string (e.g., "3.0.3" or "3.1.0"). */
  openapi: string;
  /** API metadata including title, description, and version. */
  info: { title?: string; description?: string; version?: string };
  /** Map of URL paths to their available operations. */
  paths: Record<string, PathItem>;
  /** List of server objects providing base URLs for the API. */
  servers?: ServerObject[];
  /** Global security requirements applied to all operations by default. */
  security?: SecurityRequirement[];
  /** Reusable components including security scheme definitions. */
  components?: { securitySchemes?: Record<string, SecurityScheme> };
}

/**
 * Describes the operations available on a single path.
 * Each HTTP method maps to an OperationObject.
 */
export interface PathItem {
  get?: OperationObject;
  post?: OperationObject;
  put?: OperationObject;
  delete?: OperationObject;
  patch?: OperationObject;
  head?: OperationObject;
  options?: OperationObject;
  /** Parameters shared across all operations on this path. */
  parameters?: ParameterObject[];
}

/**
 * Describes a single API operation on a path.
 */
export interface OperationObject {
  /** Tags for grouping operations in documentation. */
  tags?: string[];
  /** Short summary of the operation. */
  summary?: string;
  /** Detailed description of the operation. */
  description?: string;
  /** Unique identifier for the operation. */
  operationId?: string;
  /** Operation-level security requirements (overrides global). */
  security?: SecurityRequirement[];
  /** Map of HTTP status codes to response definitions. */
  responses?: Record<string, ResponseObject>;
  /** Parameters specific to this operation. */
  parameters?: ParameterObject[];
  /** Request body definition (not fully typed for our use case). */
  requestBody?: unknown;
}

/** Describes a server providing the API. */
export interface ServerObject {
  /** URL to the target host. */
  url: string;
  /** Optional description of the server. */
  description?: string;
}

/**
 * A security requirement object mapping scheme names to required scopes.
 */
export type SecurityRequirement = Record<string, string[]>;

/**
 * Defines a security scheme that can be used by operations.
 */
export interface SecurityScheme {
  /** The type of the security scheme. */
  type: 'apiKey' | 'http' | 'oauth2' | 'openIdConnect';
  /** Name of the header, query, or cookie parameter (for apiKey type). */
  name?: string;
  /** Location of the API key (for apiKey type). */
  in?: 'header' | 'query' | 'cookie';
  /** HTTP authorization scheme (for http type). */
  scheme?: string;
  /** OpenID Connect discovery URL (for openIdConnect type). */
  openIdConnectUrl?: string;
  /** OAuth2 flow definitions (for oauth2 type). */
  flows?: OAuthFlows;
}

/** OAuth2 flow configurations. */
export interface OAuthFlows {
  implicit?: { authorizationUrl: string; tokenUrl?: string };
  password?: { tokenUrl: string };
  clientCredentials?: { tokenUrl: string };
  authorizationCode?: { authorizationUrl: string; tokenUrl: string };
}

/** Describes a single response from an API operation. */
export interface ResponseObject {
  /** Short description of the response. */
  description?: string;
  /** Map of header names to their definitions. */
  headers?: Record<string, { schema?: { type?: string; default?: string } }>;
}

/** Describes a single operation parameter. */
export interface ParameterObject {
  /** The name of the parameter. */
  name: string;
  /** The location of the parameter. */
  in: 'path' | 'query' | 'header' | 'cookie';
  /** Whether the parameter is required. */
  required?: boolean;
  /** Schema defining the parameter type and constraints. */
  schema?: Record<string, unknown>;
}

/**
 * Result of parsing an OpenAPI specification.
 * Either succeeds with a typed spec or fails with an error message.
 */
export type ParseResult =
  | { success: true; spec: OpenApiSpec }
  | { success: false; error: string };

/**
 * Complete result of mapping an OpenAPI spec to APIGW Config Store entities.
 */
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

/**
 * Options for controlling the mapping process.
 */
export interface MapOptions {
  /** Selected server URL to use as base for target_service_uri. */
  selectedServerUrl?: string;
}

/**
 * Strategy for handling conflicts between imported data and existing configuration.
 * - 'replace': Clear all existing data and apply imported data.
 * - 'merge': Add imported data alongside existing, skipping duplicates.
 */
export type ImportStrategy = 'replace' | 'merge';
