/**
 * Pure utility functions for schema field validation and visibility.
 * Extracted from SchemaFieldRenderer for testability and reuse.
 */

import type { SchemaField } from '@/config/connection-schemas';

/**
 * Evaluates whether a field should be visible based on its visibleWhen condition.
 */
export function isFieldVisible(
  field: SchemaField,
  allValues: Record<string, string | number | boolean>,
): boolean {
  if (!field.visibleWhen) return true;
  const { field: depField, value: depValue } = field.visibleWhen;
  return allValues[depField] === depValue;
}

/**
 * Validates a field value against its validation rules.
 * Returns an error message string or null if valid.
 */
export function validateField(
  field: SchemaField,
  value: string | number | boolean | undefined,
): string | null {
  const { validation } = field;
  if (!validation) return null;

  // For required fields, check emptiness
  if (validation.required && (value === undefined || value === '' || value === null)) {
    return validation.errorMessage ?? 'This field is required';
  }

  // Skip further validation if value is empty and not required
  if (value === undefined || value === '' || value === null) return null;

  // Text field validations
  if (field.type === 'text') {
    const strValue = String(value);
    if (validation.maxLength && strValue.length > validation.maxLength) {
      return validation.errorMessage ?? `Maximum ${validation.maxLength} characters`;
    }
    if (validation.pattern && !validation.pattern.test(strValue)) {
      return validation.errorMessage ?? 'Invalid format';
    }
  }

  // Number field validations
  if (field.type === 'number') {
    const numValue = typeof value === 'string' ? Number(value) : (value as number);
    if (isNaN(numValue)) {
      return validation.errorMessage ?? 'Must be a valid number';
    }
    if (validation.min !== undefined && numValue < validation.min) {
      return validation.errorMessage ?? `Must be at least ${validation.min}`;
    }
    if (validation.max !== undefined && numValue > validation.max) {
      return validation.errorMessage ?? `Must be at most ${validation.max}`;
    }
  }

  return null;
}
