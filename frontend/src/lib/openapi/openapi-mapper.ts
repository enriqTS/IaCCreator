import type {
  OpenApiSpec,
  MapResult,
  MapOptions,
  PathItem,
  OperationObject,
  SecurityScheme,
  SecurityRequirement,
} from './types';
import type { RouteItem, AuthorizerItem } from '@/types/apigw-config';

/** HTTP methods to iterate on each PathItem. */
const HTTP_METHODS = ['get', 'post', 'put', 'delete', 'patch', 'head', 'options'] as const;

/**
 * Map a parsed OpenAPI spec into store-compatible entities.
 *
 * Extracts routes, security schemes, metadata, server URLs, and CORS configuration
 * from the spec and returns them in a format ready for the APIGW Config Store.
 */
export function mapOpenApiToConfig(spec: OpenApiSpec, options?: MapOptions): MapResult {
  const securitySchemes = spec.components?.securitySchemes ?? {};
  const globalSecurity = spec.security ?? [];

  // --- Extract authorizers from security schemes ---
  const authorizers: AuthorizerItem[] = [];
  let globalApiKeyRequired = false;

  for (const [schemeName, scheme] of Object.entries(securitySchemes)) {
    if (isApiKeyScheme(scheme)) {
      // Global api_key_required is set if the scheme exists AND is referenced globally
      // We check global reference below
    }

    if (scheme.type === 'oauth2' || scheme.type === 'openIdConnect') {
      authorizers.push({
        id: crypto.randomUUID(),
        name: schemeName,
        type: 'JWT',
        issuer_url: getIssuerUrl(scheme),
        audience: [],
      });
    }
  }

  // Determine if global security references an apiKey scheme
  for (const req of globalSecurity) {
    for (const schemeName of Object.keys(req)) {
      const scheme = securitySchemes[schemeName];
      if (scheme && isApiKeyScheme(scheme)) {
        globalApiKeyRequired = true;
      }
    }
  }

  // --- Extract routes ---
  const routes: RouteItem[] = [];

  for (const [path, pathItem] of Object.entries(spec.paths)) {
    if (!pathItem) continue;

    for (const method of HTTP_METHODS) {
      const operation = (pathItem as PathItem)[method];
      if (!operation) continue;

      const route: RouteItem = {
        id: crypto.randomUUID(),
        method: method.toUpperCase() as RouteItem['method'],
        path,
        integration_ref: '',
        integration_type: 'HTTP_PROXY',
        target_service_uri: options?.selectedServerUrl
          ? options.selectedServerUrl + path
          : undefined,
        tag: operation.tags?.[0],
        api_key_required: undefined,
        authorizer_name: undefined,
      };

      // Apply security to this route
      applySecurityToRoute(route, operation, globalSecurity, securitySchemes);

      routes.push(route);
    }
  }

  // --- Extract metadata ---
  const api_name = spec.info.title || undefined;
  const description = spec.info.description || undefined;

  // --- Extract server URLs ---
  const serverUrls = spec.servers?.map((s) => s.url) ?? [];

  // --- Detect CORS ---
  const corsConfig = detectCors(spec.paths);

  // --- Build summary ---
  const summary = {
    routeCount: routes.length,
    authorizerCount: authorizers.length,
    hasApiKey: globalApiKeyRequired || routes.some((r) => r.api_key_required === true),
    hasCors: corsConfig !== undefined,
    protocolType: 'HTTP' as const,
  };

  return {
    routes,
    authorizers,
    settings: {
      api_name,
      description,
      api_key_required: globalApiKeyRequired || undefined,
      cors_configuration: corsConfig,
      protocol_type: 'HTTP',
    },
    serverUrls,
    summary,
  };
}


/**
 * Check if a security scheme is an apiKey type with in:header and name:X-API-Key.
 */
function isApiKeyScheme(scheme: SecurityScheme): boolean {
  return (
    scheme.type === 'apiKey' &&
    scheme.in === 'header' &&
    (scheme.name?.toLowerCase() === 'x-api-key')
  );
}

/**
 * Extract the issuer URL from an oauth2 or openIdConnect security scheme.
 * For openIdConnect, uses the openIdConnectUrl.
 * For oauth2, uses the first tokenUrl found in flows.
 */
function getIssuerUrl(scheme: SecurityScheme): string | undefined {
  if (scheme.type === 'openIdConnect') {
    return scheme.openIdConnectUrl;
  }

  if (scheme.type === 'oauth2' && scheme.flows) {
    // Find the first tokenUrl from available flows
    const flows = scheme.flows;
    return (
      flows.authorizationCode?.tokenUrl ??
      flows.clientCredentials?.tokenUrl ??
      flows.password?.tokenUrl ??
      flows.implicit?.tokenUrl ??
      undefined
    );
  }

  return undefined;
}

/**
 * Apply security requirements to a route based on operation-level or global security.
 * Operation-level security overrides global. Empty security array means no auth.
 */
function applySecurityToRoute(
  route: RouteItem,
  operation: OperationObject,
  globalSecurity: SecurityRequirement[],
  securitySchemes: Record<string, SecurityScheme>
): void {
  // Determine which security requirements apply to this operation
  let effectiveSecurity: SecurityRequirement[];

  if (operation.security !== undefined) {
    // Operation-level security overrides global (including empty array = no auth)
    effectiveSecurity = operation.security;
  } else {
    effectiveSecurity = globalSecurity;
  }

  // Empty security array means explicitly no auth
  if (effectiveSecurity.length === 0 && operation.security !== undefined) {
    route.api_key_required = false;
    route.authorizer_name = undefined;
    return;
  }

  // Apply each security requirement
  for (const req of effectiveSecurity) {
    for (const schemeName of Object.keys(req)) {
      const scheme = securitySchemes[schemeName];
      if (!scheme) continue;

      if (isApiKeyScheme(scheme)) {
        route.api_key_required = true;
      }

      if (scheme.type === 'oauth2' || scheme.type === 'openIdConnect') {
        route.authorizer_name = schemeName;
      }
    }
  }
}

/**
 * Detect CORS configuration by checking for OPTIONS methods with
 * Access-Control-Allow-Origin headers in responses.
 */
function detectCors(
  paths: Record<string, PathItem>
): Record<string, string> | undefined {
  for (const pathItem of Object.values(paths)) {
    if (!pathItem?.options) continue;

    const optionsOp = pathItem.options;
    if (!optionsOp.responses) continue;

    for (const response of Object.values(optionsOp.responses)) {
      if (!response.headers) continue;

      const corsHeaders: Record<string, string> = {};

      for (const [headerName, headerDef] of Object.entries(response.headers)) {
        const lowerName = headerName.toLowerCase();
        if (lowerName.startsWith('access-control-')) {
          const value = headerDef.schema?.default ?? '';
          corsHeaders[headerName] = String(value);
        }
      }

      // If we found Access-Control-Allow-Origin, we have CORS
      const hasOriginHeader = Object.keys(corsHeaders).some(
        (h) => h.toLowerCase() === 'access-control-allow-origin'
      );

      if (hasOriginHeader) {
        return corsHeaders;
      }
    }
  }

  return undefined;
}
