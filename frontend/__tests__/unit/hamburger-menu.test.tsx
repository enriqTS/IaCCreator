import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import HamburgerMenu from '@/components/menu/HamburgerMenu';

function makeProps(overrides: Partial<Record<string, () => void>> = {}) {
  return {
    onNewDiagram: vi.fn(),
    onSave: vi.fn(),
    onLoad: vi.fn(),
    onExport: vi.fn(),
    onProjectSettings: vi.fn(),
    ...overrides,
  };
}

describe('HamburgerMenu', () => {
  it('renders the hamburger button', () => {
    render(<HamburgerMenu {...makeProps()} />);
    expect(screen.getByTestId('hamburger-button')).toBeDefined();
  });

  it('does not show dropdown initially', () => {
    render(<HamburgerMenu {...makeProps()} />);
    expect(screen.queryByTestId('hamburger-dropdown')).toBeNull();
  });

  it('shows dropdown with all 5 menu items when clicked', () => {
    render(<HamburgerMenu {...makeProps()} />);
    fireEvent.click(screen.getByTestId('hamburger-button'));

    expect(screen.getByTestId('hamburger-dropdown')).toBeDefined();
    expect(screen.getByText('New Diagram')).toBeDefined();
    expect(screen.getByText('Save')).toBeDefined();
    expect(screen.getByText('Load')).toBeDefined();
    expect(screen.getByText('Export to Terraform')).toBeDefined();
    expect(screen.getByText('Project Settings')).toBeDefined();
  });

  it('toggles dropdown closed on second click', () => {
    render(<HamburgerMenu {...makeProps()} />);
    const btn = screen.getByTestId('hamburger-button');
    fireEvent.click(btn);
    expect(screen.queryByTestId('hamburger-dropdown')).not.toBeNull();
    fireEvent.click(btn);
    expect(screen.queryByTestId('hamburger-dropdown')).toBeNull();
  });

  it('calls onNewDiagram and closes menu', () => {
    const props = makeProps();
    render(<HamburgerMenu {...props} />);
    fireEvent.click(screen.getByTestId('hamburger-button'));
    fireEvent.click(screen.getByText('New Diagram'));
    expect(props.onNewDiagram).toHaveBeenCalledOnce();
    expect(screen.queryByTestId('hamburger-dropdown')).toBeNull();
  });

  it('calls onSave and closes menu', () => {
    const props = makeProps();
    render(<HamburgerMenu {...props} />);
    fireEvent.click(screen.getByTestId('hamburger-button'));
    fireEvent.click(screen.getByText('Save'));
    expect(props.onSave).toHaveBeenCalledOnce();
    expect(screen.queryByTestId('hamburger-dropdown')).toBeNull();
  });

  it('calls onLoad and closes menu', () => {
    const props = makeProps();
    render(<HamburgerMenu {...props} />);
    fireEvent.click(screen.getByTestId('hamburger-button'));
    fireEvent.click(screen.getByText('Load'));
    expect(props.onLoad).toHaveBeenCalledOnce();
    expect(screen.queryByTestId('hamburger-dropdown')).toBeNull();
  });

  it('calls onExport and closes menu', () => {
    const props = makeProps();
    render(<HamburgerMenu {...props} />);
    fireEvent.click(screen.getByTestId('hamburger-button'));
    fireEvent.click(screen.getByText('Export to Terraform'));
    expect(props.onExport).toHaveBeenCalledOnce();
    expect(screen.queryByTestId('hamburger-dropdown')).toBeNull();
  });

  it('calls onProjectSettings and closes menu', () => {
    const props = makeProps();
    render(<HamburgerMenu {...props} />);
    fireEvent.click(screen.getByTestId('hamburger-button'));
    fireEvent.click(screen.getByText('Project Settings'));
    expect(props.onProjectSettings).toHaveBeenCalledOnce();
    expect(screen.queryByTestId('hamburger-dropdown')).toBeNull();
  });

  it('closes on outside click', () => {
    const props = makeProps();
    render(
      <div>
        <HamburgerMenu {...props} />
        <div data-testid="outside">outside</div>
      </div>
    );
    fireEvent.click(screen.getByTestId('hamburger-button'));
    expect(screen.queryByTestId('hamburger-dropdown')).not.toBeNull();

    fireEvent.mouseDown(screen.getByTestId('outside'));
    expect(screen.queryByTestId('hamburger-dropdown')).toBeNull();
  });

  it('has correct aria attributes', () => {
    render(<HamburgerMenu {...makeProps()} />);
    const btn = screen.getByTestId('hamburger-button');
    expect(btn.getAttribute('aria-label')).toBe('Menu');
    expect(btn.getAttribute('aria-expanded')).toBe('false');

    fireEvent.click(btn);
    expect(btn.getAttribute('aria-expanded')).toBe('true');
  });
});
