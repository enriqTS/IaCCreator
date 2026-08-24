import { describe, it, expect } from 'vitest';
import { render, screen, act, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ConfigOverlay from '@/components/config/overlay/ConfigOverlay';
import { useDiagramStore } from '@/store/diagram-store';
import { DEFAULT_BLOCK_VISUAL } from '@/types/diagram';
import type { ArchitectureBlock, ServiceType } from '@/types/diagram';

function makeBlock(id: string, serviceType: ServiceType): ArchitectureBlock {
  return {
    id,
    objectType: 'architecture-block',
    serviceType,
    name: id,
    position: { x: 0, y: 0 },
    config: {},
    terraformVariables: {},
    visualConfig: { ...DEFAULT_BLOCK_VISUAL },
    zIndex: 0,
  };
}

function openLambda() {
  useDiagramStore.setState({
    canvasObjects: new Map([['fn', makeBlock('fn', 'lambda')]]),
    connectors: new Map(),
    selectedObjectIds: new Set(),
    configOverlayTargetId: null,
  });
  render(<ConfigOverlay />);
  act(() => {
    useDiagramStore.getState().openConfigOverlay('fn');
  });
}

describe('A field is labelled with its name', () => {
  it('labels a field with the schema label rather than the description', () => {
    openLambda();

    const label = document.querySelector('label[for="config-field-function_name"]');
    expect(label?.textContent).toContain('Function name');
    // The sentence belongs on the info icon, not in the label
    expect(label?.textContent).not.toContain('unique name');
  });

  it('marks a required field', () => {
    openLambda();

    const required = document.querySelector('label[for="config-field-function_name"]');
    expect(required?.textContent).toContain('*');
    const optional = document.querySelector('label[for="config-field-handler"]');
    expect(optional?.textContent).not.toContain('*');
  });

  it('explains the field on an info control instead of in the label', () => {
    openLambda();

    expect(screen.getByLabelText('What Function name does')).toBeDefined();
  });
});

describe('Renaming happens in the panel', () => {
  it('offers the name first, and writes it back to the object', async () => {
    const user = userEvent.setup();
    openLambda();

    const field = screen.getByTestId('object-name-field');
    await user.clear(field);
    await user.type(field, 'orders');

    expect(useDiagramStore.getState().canvasObjects.get('fn')?.name).toBe('orders');
  });
});

describe('An invalid field is findable from any tab', () => {
  async function breakTimeout(user: ReturnType<typeof userEvent.setup>) {
    await user.click(screen.getByTestId('schema-tab-performance'));
    fireEvent.change(screen.getByTestId('field-timeout'), { target: { value: '1200' } });
  }

  it('marks the tab the invalid field sits on', async () => {
    const user = userEvent.setup();
    openLambda();
    await breakTimeout(user);

    await user.click(screen.getByTestId('schema-tab-general'));

    expect(screen.getByTestId('schema-tab-performance-error')).toBeDefined();
  });

  it('names the field and its tab in the summary', async () => {
    const user = userEvent.setup();
    openLambda();
    await breakTimeout(user);

    const summary = screen.getByTestId('validation-error-summary');
    expect(summary.textContent).toContain('1 field needs attention');
    expect(summary.textContent).toContain('Timeout');
    expect(summary.textContent).toContain('Performance');
  });

  it('opens the tab the field is on when the summary is used', async () => {
    const user = userEvent.setup();
    openLambda();
    await breakTimeout(user);
    await user.click(screen.getByTestId('schema-tab-general'));

    await user.click(screen.getByTestId('validation-jump-timeout'));

    expect(screen.getByTestId('config-group-Performance')).toBeDefined();
  });
});
