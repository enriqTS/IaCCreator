import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import VariablesPanel from '@/components/config/VariablesPanel';
import { useDiagramStore } from '@/store/diagram-store';
import type { ArchitectureBlock } from '@/types/diagram';
import { getDefaultVariables } from '@/types/terraform-variables';

function makeBlock(
  serviceType: ArchitectureBlock['serviceType'],
  overrides: Record<string, string | number | boolean> = {},
): ArchitectureBlock {
  return {
    id: 'block-1',
    objectType: 'architecture-block',
    serviceType,
    name: `test-${serviceType}`,
    position: { x: 0, y: 0 },
    config: {},
    terraformVariables: { ...getDefaultVariables(serviceType), ...overrides },
    visualConfig: { width: 80, height: 80 },
    zIndex: 0,
  };
}

describe('VariablesPanel', () => {
  beforeEach(() => {
    useDiagramStore.setState({});
  });

  // --- Requirement 3.4: string variables render text inputs ---
  it('renders text inputs for string variables (lambda)', () => {
    const block = makeBlock('lambda');
    render(<VariablesPanel block={block} />);

    const fnName = screen.getByTestId('var-function_name');
    expect(fnName).toBeDefined();
    expect(fnName.getAttribute('type')).toBe('text');

    const handler = screen.getByTestId('var-handler');
    expect(handler.getAttribute('type')).toBe('text');

    const runtime = screen.getByTestId('var-runtime');
    expect(runtime.getAttribute('type')).toBe('text');
  });

  // --- Requirement 3.5: number variables render numeric text inputs (no spinners) ---
  it('renders numeric text inputs for number variables (lambda)', () => {
    const block = makeBlock('lambda');
    render(<VariablesPanel block={block} />);

    const memorySize = screen.getByTestId('var-memory_size');
    expect(memorySize.getAttribute('type')).toBe('text');
    expect(memorySize.getAttribute('inputmode')).toBe('numeric');

    const timeout = screen.getByTestId('var-timeout');
    expect(timeout.getAttribute('type')).toBe('text');
    expect(timeout.getAttribute('inputmode')).toBe('numeric');
  });

  // --- Requirement 3.6: bool variables render shadcn/ui Checkbox (button role) ---
  it('renders checkbox for bool variables (s3)', () => {
    const block = makeBlock('s3');
    render(<VariablesPanel block={block} />);

    const versioning = screen.getByTestId('var-versioning_enabled');
    expect(versioning.getAttribute('role')).toBe('checkbox');
  });

  // --- Requirement 3.2: correct fields per service type ---
  it('renders all schema fields for dynamodb', () => {
    const block = makeBlock('dynamodb');
    render(<VariablesPanel block={block} />);

    expect(screen.getByTestId('var-table_name').getAttribute('type')).toBe('text');
    expect(screen.getByTestId('var-billing_mode').getAttribute('type')).toBe('text');
    expect(screen.getByTestId('var-hash_key').getAttribute('type')).toBe('text');
    expect(screen.getByTestId('var-hash_key_type').getAttribute('type')).toBe('text');
    expect(screen.getByTestId('var-range_key').getAttribute('type')).toBe('text');
    expect(screen.getByTestId('var-range_key_type').getAttribute('type')).toBe('text');
  });

  it('renders all schema fields for api-gateway', () => {
    const block = makeBlock('api-gateway');
    render(<VariablesPanel block={block} />);

    expect(screen.getByTestId('var-api_name').getAttribute('type')).toBe('text');
    expect(screen.getByTestId('var-protocol_type').getAttribute('type')).toBe('text');
  });

  it('renders all schema fields for cloudwatch', () => {
    const block = makeBlock('cloudwatch');
    render(<VariablesPanel block={block} />);

    expect(screen.getByTestId('var-log_group_name').getAttribute('type')).toBe('text');
    expect(screen.getByTestId('var-retention_in_days').getAttribute('type')).toBe('text');
    expect(screen.getByTestId('var-retention_in_days').getAttribute('inputmode')).toBe('numeric');
  });

  // --- Requirement 3.8: required indicator for required fields (shown as subtle *, not red borders) ---
  it('shows required indicator for empty required string fields', () => {
    // function_name, handler, runtime have no defaults → required
    const block = makeBlock('lambda');
    render(<VariablesPanel block={block} />);

    expect(screen.getByTestId('required-function_name')).toBeDefined();
    expect(screen.getByTestId('required-handler')).toBeDefined();
    expect(screen.getByTestId('required-runtime')).toBeDefined();
  });

  it('does not show required indicator for fields with defaults', () => {
    // memory_size and timeout have defaults → not required
    const block = makeBlock('lambda');
    render(<VariablesPanel block={block} />);

    expect(screen.queryByTestId('required-memory_size')).toBeNull();
    expect(screen.queryByTestId('required-timeout')).toBeNull();
  });

  it('does not hide required indicator when field has a value (always shown for required fields)', () => {
    const block = makeBlock('lambda', {
      function_name: 'my-func',
      handler: 'index.handler',
      runtime: 'python3.12',
    });
    render(<VariablesPanel block={block} />);

    // Required indicator is always shown for required fields regardless of value
    expect(screen.getByTestId('required-function_name')).toBeDefined();
    expect(screen.getByTestId('required-handler')).toBeDefined();
    expect(screen.getByTestId('required-runtime')).toBeDefined();
  });

  it('shows required indicator for required dynamodb fields but not optional ones', () => {
    // table_name and hash_key are required; range_key is optional
    const block = makeBlock('dynamodb');
    render(<VariablesPanel block={block} />);

    expect(screen.getByTestId('required-table_name')).toBeDefined();
    expect(screen.getByTestId('required-hash_key')).toBeDefined();
    expect(screen.queryByTestId('required-range_key')).toBeNull();
  });

  it('shows empty message for unsupported service type', () => {
    const block = makeBlock('iam' as ArchitectureBlock['serviceType']);
    render(<VariablesPanel block={block} />);

    expect(screen.queryByTestId('variables-panel')).toBeNull();
    expect(screen.getByText('No variables defined for this service type.')).toBeDefined();
  });
});
