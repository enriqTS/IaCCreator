import { describe, it, expect } from 'vitest';
import { isFieldVisible, validateField } from '@/components/config/schema-field-utils';
import type { SchemaField } from '@/config/connection-schemas';

describe('SchemaFieldRenderer - isFieldVisible', () => {
  it('returns true when field has no visibleWhen condition', () => {
    const field: SchemaField = {
      key: 'batch_size',
      label: 'Batch Size',
      type: 'number',
    };
    expect(isFieldVisible(field, {})).toBe(true);
  });

  it('returns true when visibleWhen condition is met', () => {
    const field: SchemaField = {
      key: 'http_method',
      label: 'HTTP Method',
      type: 'select',
      visibleWhen: { field: 'connection_role', value: 'route_handler' },
    };
    expect(isFieldVisible(field, { connection_role: 'route_handler' })).toBe(true);
  });

  it('returns false when visibleWhen condition is not met', () => {
    const field: SchemaField = {
      key: 'http_method',
      label: 'HTTP Method',
      type: 'select',
      visibleWhen: { field: 'connection_role', value: 'route_handler' },
    };
    expect(isFieldVisible(field, { connection_role: 'authorizer' })).toBe(false);
  });

  it('returns false when dependent field is not present in allValues', () => {
    const field: SchemaField = {
      key: 'route_path',
      label: 'Route Path',
      type: 'text',
      visibleWhen: { field: 'connection_role', value: 'route_handler' },
    };
    expect(isFieldVisible(field, {})).toBe(false);
  });
});

describe('SchemaFieldRenderer - validateField', () => {
  describe('text fields', () => {
    const routePathField: SchemaField = {
      key: 'route_path',
      label: 'Route Path',
      type: 'text',
      validation: {
        required: true,
        pattern: /^\/[\w\-/{}\$]*$/,
        maxLength: 128,
        errorMessage: 'Must start with / and contain only alphanumeric, /, -, _, {, }, $',
      },
    };

    it('returns null for valid value', () => {
      expect(validateField(routePathField, '/users/{id}')).toBeNull();
    });

    it('returns error for required empty value', () => {
      expect(validateField(routePathField, '')).toBe(routePathField.validation!.errorMessage);
    });

    it('returns error for invalid pattern', () => {
      expect(validateField(routePathField, 'no-leading-slash')).toBe(routePathField.validation!.errorMessage);
    });

    it('returns error when maxLength exceeded', () => {
      const longPath = '/' + 'a'.repeat(128);
      expect(validateField(routePathField, longPath)).toBe(routePathField.validation!.errorMessage);
    });

    it('returns null when value is empty and not required', () => {
      const optionalField: SchemaField = {
        key: 'name',
        label: 'Name',
        type: 'text',
        validation: { pattern: /^[\w]+$/ },
      };
      expect(validateField(optionalField, '')).toBeNull();
    });
  });

  describe('number fields', () => {
    const batchSizeField: SchemaField = {
      key: 'batch_size',
      label: 'Batch Size',
      type: 'number',
      validation: { min: 1, max: 10000, errorMessage: 'Must be between 1 and 10000' },
    };

    it('returns null for valid number', () => {
      expect(validateField(batchSizeField, 10)).toBeNull();
    });

    it('returns error when below min', () => {
      expect(validateField(batchSizeField, 0)).toBe('Must be between 1 and 10000');
    });

    it('returns error when above max', () => {
      expect(validateField(batchSizeField, 10001)).toBe('Must be between 1 and 10000');
    });

    it('returns null for empty value (optional)', () => {
      expect(validateField(batchSizeField, '')).toBeNull();
    });

    it('returns error for NaN string', () => {
      expect(validateField(batchSizeField, 'abc' as unknown as number)).toBe('Must be between 1 and 10000');
    });
  });

  describe('fields without validation', () => {
    it('returns null when no validation rules exist', () => {
      const field: SchemaField = {
        key: 'access_pattern',
        label: 'Access Pattern',
        type: 'select',
      };
      expect(validateField(field, 'read')).toBeNull();
    });
  });
});
