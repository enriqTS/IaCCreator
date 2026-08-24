import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import FieldLabel from '@/components/config/schema/FieldLabel';

describe('FieldLabel', () => {
  it('does not activate the field it labels when the explanation is opened', async () => {
    const user = userEvent.setup();
    render(
      <>
        <FieldLabel label="Publish" description="Publish a new version" htmlFor="publish" />
        <input id="publish" type="checkbox" />
      </>,
    );
    const checkbox = screen.getByRole('checkbox') as HTMLInputElement;

    await user.click(screen.getByLabelText('What Publish does'));

    expect(checkbox.checked).toBe(false);
  });

  it('still focuses the field when the label itself is clicked', async () => {
    const user = userEvent.setup();
    render(
      <>
        <FieldLabel label="Handler" description="The entrypoint" htmlFor="handler" />
        <input id="handler" type="text" />
      </>,
    );

    await user.click(screen.getByText('Handler'));

    expect(document.activeElement).toBe(screen.getByRole('textbox'));
  });
});
