/**
 * Schema store — fetches variable schemas from the backend API,
 * caches in memory, and falls back to a bundled copy when the API is unreachable.
 */

import type { ServiceVariableSchemas } from '@/types/terraform-variables';
import { BUNDLED_SCHEMAS } from '@/data/bundled-schemas';

let cachedSchemas: ServiceVariableSchemas | null = null;

/**
 * Fetch variable schemas from the backend `/api/variable-schemas` endpoint.
 * Caches the result in memory on first successful fetch.
 * Falls back to the bundled schemas if the fetch fails.
 */
export async function fetchSchemas(): Promise<ServiceVariableSchemas> {
  if (cachedSchemas) return cachedSchemas;

  try {
    const res = await fetch('/api/variable-schemas');
    if (!res.ok) {
      throw new Error(`Schema fetch failed: ${res.status}`);
    }
    cachedSchemas = await res.json();
    return cachedSchemas!;
  } catch {
    console.warn('Failed to fetch variable schemas from API, using bundled fallback.');
    cachedSchemas = BUNDLED_SCHEMAS;
    return cachedSchemas;
  }
}

/**
 * Return the cached schemas synchronously, or the bundled fallback if not yet fetched.
 */
export function getSchemas(): ServiceVariableSchemas {
  return cachedSchemas ?? BUNDLED_SCHEMAS;
}

/**
 * Clear the cached schemas (useful for testing).
 */
export function clearSchemaCache(): void {
  cachedSchemas = null;
}
