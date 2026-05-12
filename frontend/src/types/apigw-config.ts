/**
 * Type definitions for the API Gateway Dynamic Config UI.
 *
 * These interfaces define the shape of collection items managed by the
 * APIGW Config Store and rendered in the dynamic configuration panels.
 */

/**
 * The API Gateway protocol type, determining which tabs and fields
 * are displayed in the Dynamic Config UI.
 */
export type ProtocolType = 'HTTP' | 'REST' | 'WEBSOCKET';

/**
 * A single route entry in the Routes collection.
 * Represents an HTTP/REST API route with method, path, and integration settings.
 */
export interface RouteItem {
  /** Unique identifier for stable list rendering and selection tracking. */
  id: string;
  /** HTTP method for this route. */
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' | 'HEAD' | 'OPTIONS' | 'ANY';
  /** URL path pattern for this route (e.g., "/users/{id}"). */
  path: string;
  /** Reference to the integration ID or empty string if unset. */
  integration_ref: string;
  /** The type of backend integration for this route. */
  integration_type?: 'HTTP_PROXY' | 'HTTP' | 'AWS_PROXY' | 'MOCK';
  /** HTTP method used for the backend integration (shown for HTTP_PROXY/HTTP). */
  integration_method?: string;
  /** Payload format version for Lambda proxy integrations (shown for AWS_PROXY). */
  payload_format_version?: '1.0' | '2.0';
}

/**
 * A single stage entry in the Stages collection.
 * Represents a deployment stage with throttling, logging, and variable settings.
 */
export interface StageItem {
  /** Unique identifier for stable list rendering and selection tracking. */
  id: string;
  /** Stage name (e.g., "$default", "prod", "dev"). */
  name: string;
  /** Whether deployments are automatically published to this stage. */
  auto_deploy: boolean;
  /** Key-value pairs of stage variables (max 50 entries). */
  stage_variables: Record<string, string>;
  /** Maximum number of requests per second in a burst (1–5000). */
  throttling_burst_limit: number;
  /** Steady-state request rate limit per second (1.0–10000.0). */
  throttling_rate_limit: number;
  /** Whether access logging is enabled for this stage. */
  access_logging: boolean;
  /** Number of days to retain access logs (shown when access_logging is true). */
  log_retention_days?: number;
  /** Custom log format string (shown when access_logging is true). */
  log_format?: string;
}

/**
 * A single authorizer entry in the Authorizers collection.
 * Fields are conditionally displayed based on the authorizer type.
 */
export interface AuthorizerItem {
  /** Unique identifier for stable list rendering and selection tracking. */
  id: string;
  /** Display name for this authorizer. */
  name: string;
  /** The authorization strategy type. */
  type: 'JWT' | 'REQUEST' | 'COGNITO_USER_POOLS';
  /** JWT issuer URL (shown when type is "JWT"). */
  issuer_url?: string;
  /** List of accepted audience values (shown when type is "JWT"). */
  audience?: string[];
  /** ARN of the Lambda authorizer function (shown when type is "REQUEST"). */
  lambda_function_arn?: string;
  /** Payload format version for Lambda authorizer (shown when type is "REQUEST"). */
  payload_format_version?: '1.0' | '2.0';
  /** Cognito User Pool endpoint URL (shown when type is "COGNITO_USER_POOLS"). */
  cognito_endpoint?: string;
  /** List of app client IDs for the Cognito User Pool (shown when type is "COGNITO_USER_POOLS"). */
  client_ids?: string[];
}

/**
 * A single WebSocket route entry in the Expressions collection.
 * Special routes ($connect, $disconnect, $default) are pre-populated and non-removable.
 */
export interface WebSocketRouteItem {
  /** Unique identifier for stable list rendering and selection tracking. */
  id: string;
  /** The route key expression (e.g., "$connect", "$disconnect", "$default", or custom). */
  route_key: string;
  /** Whether this is a special route ($connect, $disconnect, $default) that cannot be removed. */
  is_special: boolean;
  /** Whether authorization is enabled for this route (only configurable for $connect). */
  authorization_enabled: boolean;
}
