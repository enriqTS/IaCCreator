/**
 * Naming rules store — the backend defines what a resource may be called;
 * this fetches the rule so the editor can check a name before submitting.
 */

export interface NamingRules {
  pattern: RegExp;
  description: string;
  maxLength: number;
}

let rules: NamingRules | null = null;

/** Fetch the naming rules once and cache them. */
export async function fetchNamingRules(): Promise<boolean> {
  if (rules) return true;
  try {
    const res = await fetch('/api/naming-rules');
    if (!res.ok) throw new Error(`Naming rules fetch failed: ${res.status}`);
    const body: { pattern: string; description: string; max_length: number } =
      await res.json();
    rules = {
      pattern: new RegExp(body.pattern),
      description: body.description,
      maxLength: body.max_length,
    };
    return true;
  } catch {
    console.warn('Could not load naming rules; names are checked by the server only.');
    return false;
  }
}

/**
 * Check a proposed resource name against the backend rule.
 * Returns an error message, or null when the name is acceptable or the rule is unknown.
 */
export function validateResourceName(name: string): string | null {
  if (!rules) return null;
  if (name.length > rules.maxLength) {
    return `Name must be at most ${rules.maxLength} characters`;
  }
  return rules.pattern.test(name) ? null : rules.description;
}

/** Clear the cached rules (used by tests). */
export function clearNamingRulesCache(): void {
  rules = null;
}
