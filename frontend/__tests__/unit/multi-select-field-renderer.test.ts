import { describe, it, expect, vi } from 'vitest';
import type { SchemaField } from '@/config/connection-schemas';

/**
 * Tests for MultiSelectFieldRenderer logic.
 * We extract and test the core toggle/serialization logic directly.
 */

// --- Extracted logic from MultiSelectFieldRenderer for unit testing ---

function parseValue(value: string | number | boolean | undefined, defaultValue?: string | number | boolean): Set<string> {
  const rawValue = value !== undefined && value !== null && value !== ''
    ? String(value)
    : (defaultValue !== undefined ? String(defaultValue) : '');

  if (!rawValue) return new Set<string>();
  return new Set(rawValue.split(',').filter(Boolean));
}

function serialize(selected: Set<string>, options: { value: string }[]): string {
  return options
    .map((opt) => opt.value)
    .filter((v) => selected.has(v))
    .join(',');
}

function handleToggle(
  toggledValue: string,
  currentSelected: Set<string>,
  exclusiveValues: Set<string>,
): Set<string> {
  const newSelected = new Set(currentSelected);

  if (newSelected.has(toggledValue)) {
    newSelected.delete(toggledValue);
  } else {
    if (exclusiveValues.has(toggledValue)) {
      newSelected.clear();
      newSelected.add(toggledValue);
    } else {
      for (const excl of exclusiveValues) {
        newSelected.delete(excl);
      }
      newSelected.add(toggledValue);
    }
  }

  return newSelected;
}

// --- Tests ---

const httpMethodOptions = [
  { value: 'GET', label: 'GET' },
  { value: 'POST', label: 'POST' },
  { value: 'PUT', label: 'PUT' },
  { value: 'DELETE', label: 'DELETE' },
  { value: 'PATCH', label: 'PATCH' },
  { value: 'OPTIONS', label: 'OPTIONS' },
  { value: 'HEAD', label: 'HEAD' },
  { value: 'ANY', label: 'ANY' },
];

const exclusiveValues = new Set(['ANY']);

describe('MultiSelectFieldRenderer - parseValue', () => {
  it('parses comma-separated string into a Set', () => {
    const result = parseValue('GET,POST,DELETE');
    expect(result).toEqual(new Set(['GET', 'POST', 'DELETE']));
  });

  it('returns empty set for empty string', () => {
    const result = parseValue('');
    expect(result).toEqual(new Set());
  });

  it('returns empty set for undefined value with no default', () => {
    const result = parseValue(undefined);
    expect(result).toEqual(new Set());
  });

  it('uses defaultValue when value is undefined', () => {
    const result = parseValue(undefined, 'ANY');
    expect(result).toEqual(new Set(['ANY']));
  });

  it('uses defaultValue when value is empty string', () => {
    const result = parseValue('', 'GET,POST');
    expect(result).toEqual(new Set(['GET', 'POST']));
  });

  it('parses single value', () => {
    const result = parseValue('GET');
    expect(result).toEqual(new Set(['GET']));
  });
});

describe('MultiSelectFieldRenderer - serialize', () => {
  it('serializes selected values in schema options order', () => {
    const selected = new Set(['DELETE', 'GET', 'POST']);
    const result = serialize(selected, httpMethodOptions);
    expect(result).toBe('GET,POST,DELETE');
  });

  it('returns empty string for empty set', () => {
    const selected = new Set<string>();
    const result = serialize(selected, httpMethodOptions);
    expect(result).toBe('');
  });

  it('serializes single value', () => {
    const selected = new Set(['ANY']);
    const result = serialize(selected, httpMethodOptions);
    expect(result).toBe('ANY');
  });

  it('maintains schema order regardless of insertion order', () => {
    const selected = new Set(['PATCH', 'GET', 'HEAD', 'POST']);
    const result = serialize(selected, httpMethodOptions);
    expect(result).toBe('GET,POST,PATCH,HEAD');
  });
});

describe('MultiSelectFieldRenderer - handleToggle', () => {
  describe('basic toggle behavior', () => {
    it('adds a value when not selected', () => {
      const current = new Set(['GET']);
      const result = handleToggle('POST', current, exclusiveValues);
      expect(result).toEqual(new Set(['GET', 'POST']));
    });

    it('removes a value when already selected', () => {
      const current = new Set(['GET', 'POST']);
      const result = handleToggle('POST', current, exclusiveValues);
      expect(result).toEqual(new Set(['GET']));
    });

    it('can deselect all values resulting in empty set', () => {
      const current = new Set(['GET']);
      const result = handleToggle('GET', current, exclusiveValues);
      expect(result).toEqual(new Set());
    });
  });

  describe('exclusive option logic', () => {
    it('selecting exclusive value deselects all others', () => {
      const current = new Set(['GET', 'POST', 'DELETE']);
      const result = handleToggle('ANY', current, exclusiveValues);
      expect(result).toEqual(new Set(['ANY']));
    });

    it('selecting non-exclusive value while exclusive is selected deselects exclusive', () => {
      const current = new Set(['ANY']);
      const result = handleToggle('GET', current, exclusiveValues);
      expect(result).toEqual(new Set(['GET']));
    });

    it('deselecting exclusive value results in empty set', () => {
      const current = new Set(['ANY']);
      const result = handleToggle('ANY', current, exclusiveValues);
      expect(result).toEqual(new Set());
    });

    it('selecting multiple non-exclusive values does not trigger exclusive logic', () => {
      const current = new Set(['GET', 'POST']);
      const result = handleToggle('DELETE', current, exclusiveValues);
      expect(result).toEqual(new Set(['GET', 'POST', 'DELETE']));
    });
  });

  describe('no exclusive values configured', () => {
    const noExclusive = new Set<string>();

    it('toggles normally without exclusive logic', () => {
      const current = new Set(['GET']);
      const result = handleToggle('POST', current, noExclusive);
      expect(result).toEqual(new Set(['GET', 'POST']));
    });

    it('removes value normally', () => {
      const current = new Set(['GET', 'POST']);
      const result = handleToggle('GET', current, noExclusive);
      expect(result).toEqual(new Set(['POST']));
    });
  });
});

describe('MultiSelectFieldRenderer - integration of parse/toggle/serialize', () => {
  it('full flow: parse → toggle → serialize maintains order', () => {
    const selected = parseValue('GET,DELETE');
    const afterToggle = handleToggle('POST', selected, exclusiveValues);
    const result = serialize(afterToggle, httpMethodOptions);
    expect(result).toBe('GET,POST,DELETE');
  });

  it('full flow: exclusive toggle resets to single value', () => {
    const selected = parseValue('GET,POST,DELETE');
    const afterToggle = handleToggle('ANY', selected, exclusiveValues);
    const result = serialize(afterToggle, httpMethodOptions);
    expect(result).toBe('ANY');
  });

  it('full flow: breaking out of exclusive adds only the new value', () => {
    const selected = parseValue('ANY');
    const afterToggle = handleToggle('POST', selected, exclusiveValues);
    const result = serialize(afterToggle, httpMethodOptions);
    expect(result).toBe('POST');
  });

  it('validation: empty set after deselecting last value', () => {
    const selected = parseValue('GET');
    const afterToggle = handleToggle('GET', selected, exclusiveValues);
    expect(afterToggle.size).toBe(0);
    const result = serialize(afterToggle, httpMethodOptions);
    expect(result).toBe('');
  });
});
