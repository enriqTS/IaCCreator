import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import HamburgerMenu from '@/components/menu/HamburgerMenu';
import { useLayoutPreferencesStore } from '@/store/layout-preferences-store';

function makeProps(overrides: Partial<Record<string, () => void>> = {}) {
  return {
    onNewDiagram: vi.fn(),
    onSave: vi.fn(),
    onLoad: vi.fn(),
    onExport: vi.fn(),
    onProjectSettings: vi.fn(),
    onPreferences: vi.fn(),
    ...overrides,
  };
}

beforeEach(() => {
  useLayoutPreferencesStore.setState({ sidebarSide: 'right', toolbarPosition: 'top' });
});

describe('HamburgerMenu', () => {
  it('renders the hamburger button', () => {
    render(<HamburgerMenu {...makeProps()} />);
    expect(screen.getByTestId('hamburger-button')).toBeDefined();
  });

  it('does not show dropdown initially', () => {
    render(<HamburgerMenu {...makeProps()} />);
    expect(screen.queryByTestId('hamburger-dropdown')).toBeNull();
  });

  it('shows dropdown with all 6 menu items when clicked', async () => {
    const user = userEvent.setup();
    render(<HamburgerMenu {...makeProps()} />);
    await user.click(screen.getByTestId('hamburger-button'));

    expect(screen.getByTestId('hamburger-dropdown')).toBeDefined();
    expect(screen.getByText('New Diagram')).toBeDefined();
    expect(screen.getByText('Save')).toBeDefined();
    expect(screen.getByText('Load')).toBeDefined();
    expect(screen.getByText('Export to Terraform')).toBeDefined();
    expect(screen.getByText('Project Settings')).toBeDefined();
    expect(screen.getByText('Preferences')).toBeDefined();
  });

  it('calls onNewDiagram when New Diagram is clicked', async () => {
    const user = userEvent.setup();
    const props = makeProps();
    render(<HamburgerMenu {...props} />);
    await user.click(screen.getByTestId('hamburger-button'));
    await user.click(screen.getByText('New Diagram'));
    expect(props.onNewDiagram).toHaveBeenCalledOnce();
  });

  it('calls onSave when Save is clicked', async () => {
    const user = userEvent.setup();
    const props = makeProps();
    render(<HamburgerMenu {...props} />);
    await user.click(screen.getByTestId('hamburger-button'));
    await user.click(screen.getByText('Save'));
    expect(props.onSave).toHaveBeenCalledOnce();
  });

  it('calls onLoad when Load is clicked', async () => {
    const user = userEvent.setup();
    const props = makeProps();
    render(<HamburgerMenu {...props} />);
    await user.click(screen.getByTestId('hamburger-button'));
    await user.click(screen.getByText('Load'));
    expect(props.onLoad).toHaveBeenCalledOnce();
  });

  it('calls onExport when Export to Terraform is clicked', async () => {
    const user = userEvent.setup();
    const props = makeProps();
    render(<HamburgerMenu {...props} />);
    await user.click(screen.getByTestId('hamburger-button'));
    await user.click(screen.getByText('Export to Terraform'));
    expect(props.onExport).toHaveBeenCalledOnce();
  });

  it('calls onProjectSettings when Project Settings is clicked', async () => {
    const user = userEvent.setup();
    const props = makeProps();
    render(<HamburgerMenu {...props} />);
    await user.click(screen.getByTestId('hamburger-button'));
    await user.click(screen.getByText('Project Settings'));
    expect(props.onProjectSettings).toHaveBeenCalledOnce();
  });

  it('calls onPreferences when Preferences is clicked', async () => {
    const user = userEvent.setup();
    const props = makeProps();
    render(<HamburgerMenu {...props} />);
    await user.click(screen.getByTestId('hamburger-button'));
    await user.click(screen.getByText('Preferences'));
    expect(props.onPreferences).toHaveBeenCalledOnce();
  });

  it('has correct aria-label on the button', () => {
    render(<HamburgerMenu {...makeProps()} />);
    const btn = screen.getByTestId('hamburger-button');
    expect(btn.getAttribute('aria-label')).toBe('Menu');
  });

  it('positions at top-left when sidebarSide is right', () => {
    useLayoutPreferencesStore.setState({ sidebarSide: 'right' });
    render(<HamburgerMenu {...makeProps()} />);
    const container = screen.getByTestId('hamburger-menu');
    expect(container.style.left).toBe('16px');
    expect(container.style.right).toBe('');
  });

  it('positions at top-right when sidebarSide is left', () => {
    useLayoutPreferencesStore.setState({ sidebarSide: 'left' });
    render(<HamburgerMenu {...makeProps()} />);
    const container = screen.getByTestId('hamburger-menu');
    expect(container.style.right).toBe('16px');
    expect(container.style.left).toBe('');
  });
});
