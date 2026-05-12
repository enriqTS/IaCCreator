import yaml from 'js-yaml';
import type { ParseResult, OpenApiSpec } from './types';

/**
 * Parse raw text content into an OpenApiSpec.
 * Attempts JSON.parse first, falls back to js-yaml.
 * Validates structural requirements (openapi version field, info object, paths object).
 */
export function parseOpenApiSpec(content: string): ParseResult {
  let parsed: unknown;

  // Step 1: Try JSON.parse first
  try {
    parsed = JSON.parse(content);
  } catch {
    // Step 2: If JSON fails, try YAML
    try {
      parsed = yaml.load(content);
    } catch {
      return {
        success: false,
        error: 'Invalid format: content is not valid JSON or YAML',
      };
    }
  }

  // Ensure we got an object
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    return {
      success: false,
      error: 'Invalid format: content is not valid JSON or YAML',
    };
  }

  const doc = parsed as Record<string, unknown>;

  // Step 4: Validate openapi version field
  if (
    typeof doc.openapi !== 'string' ||
    !doc.openapi.startsWith('3.')
  ) {
    return {
      success: false,
      error: "Not a valid OpenAPI 3.x document: missing or unsupported 'openapi' version field",
    };
  }

  // Validate info object
  if (typeof doc.info !== 'object' || doc.info === null || Array.isArray(doc.info)) {
    return {
      success: false,
      error: "Not a valid OpenAPI 3.x document: missing 'info' object",
    };
  }

  // Validate paths object
  if (typeof doc.paths !== 'object' || doc.paths === null || Array.isArray(doc.paths)) {
    return {
      success: false,
      error: "Not a valid OpenAPI 3.x document: missing 'paths' object",
    };
  }

  // All validations pass
  return {
    success: true,
    spec: parsed as OpenApiSpec,
  };
}
