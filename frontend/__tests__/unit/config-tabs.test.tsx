import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { useState } from 'react';
import ConfigTabs, { type ConfigTab } from '@/components/config/overlay/ConfigTabs';

function Harness({ tabs }: { tabs: ConfigTab[] }) {
  const [value, setValue] = useState('');
  return (
    <ConfigTabs testIdPrefix="test" tabs={tabs} value={value} onValueChange={setValue} />
  );
}

const twoTabs: ConfigTab[] = [
  { id: 'General', label: 'General', content: <span>general body</span> },
  { id: 'Advanced', label: 'Advanced', content: <span>advanced body</span> },
];

/** jsdom reports zero-size boxes, so overflow has to be described to the element. */
function makeOverflowing(strip: HTMLElement, scrollLeft = 0) {
  Object.defineProperty(strip, 'clientWidth', { value: 200, configurable: true });
  Object.defineProperty(strip, 'scrollWidth', { value: 600, configurable: true });
  Object.defineProperty(strip, 'scrollLeft', { value: scrollLeft, configurable: true });
  fireEvent.scroll(strip);
}

describe('ConfigTabs', () => {
  it('shows one trigger per tab and opens the first by default', () => {
    render(<Harness tabs={twoTabs} />);

    expect(screen.getByTestId('test-tab-general')).toBeDefined();
    expect(screen.getByTestId('test-tab-advanced')).toBeDefined();
    expect(screen.getByText('general body')).toBeDefined();
  });

  it('switches the body when another tab is chosen', () => {
    render(<Harness tabs={twoTabs} />);

    fireEvent.mouseDown(screen.getByTestId('test-tab-advanced'), { button: 0 });

    expect(screen.getByText('advanced body')).toBeDefined();
  });

  it('scrolls the strip across only, never down', () => {
    render(<Harness tabs={twoTabs} />);

    // Tailwind classes are the only evidence available: jsdom computes no styles,
    // and overflow-y left unstated is exactly what CSS turns back into a scroller
    const strip = screen.getByTestId('test-tab-strip');
    expect(strip.className).toContain('overflow-x-auto');
    expect(strip.className).toContain('overflow-y-hidden');
  });

  it('lets every box above the strip shrink below the tab row', () => {
    render(<Harness tabs={twoTabs} />);

    // Flex and grid items default to min-width:auto, which floors them at their
    // content width — the strip then grows instead of scrolling
    const strip = screen.getByTestId('test-tab-strip');
    const wrapper = strip.parentElement as HTMLElement;
    const root = wrapper.parentElement as HTMLElement;
    expect(wrapper.className).toContain('min-w-0');
    expect(root.className).toContain('min-w-0');
  });

  it('shows no scroll arrows while every tab fits', () => {
    render(<Harness tabs={twoTabs} />);

    expect(screen.queryByTestId('test-tab-scroll-left')).toBeNull();
    expect(screen.queryByTestId('test-tab-scroll-right')).toBeNull();
  });

  it('marks a tab whose contents have a problem, so a closed tab still shows it', () => {
    render(
      <Harness
        tabs={[twoTabs[0], { ...twoTabs[1], status: 'error' }]}
      />,
    );

    expect(screen.getByTestId('test-tab-advanced-error')).toBeDefined();
    expect(screen.queryByTestId('test-tab-general-error')).toBeNull();
  });
});

describe('ConfigTabs overflow', () => {
  const manyTabs: ConfigTab[] = Array.from({ length: 8 }, (_, i) => ({
    id: `Tab${i}`,
    label: `Tab ${i}`,
    content: <span>body {i}</span>,
  }));

  it('offers a forward arrow once the tabs overflow the strip', () => {
    render(<Harness tabs={manyTabs} />);

    makeOverflowing(screen.getByTestId('test-tab-strip'));

    expect(screen.getByTestId('test-tab-scroll-right').hasAttribute('disabled')).toBe(false);
    // Both arrows stay put so the strip keeps its width; there is just nothing to go back to
    expect(screen.getByTestId('test-tab-scroll-left').hasAttribute('disabled')).toBe(true);
  });

  it('offers a back arrow once the strip has been scrolled', () => {
    render(<Harness tabs={manyTabs} />);

    makeOverflowing(screen.getByTestId('test-tab-strip'), 120);

    expect(screen.getByTestId('test-tab-scroll-left').hasAttribute('disabled')).toBe(false);
  });

  it('keeps the arrows out of the strip so no tab sits underneath one', () => {
    render(<Harness tabs={manyTabs} />);
    const strip = screen.getByTestId('test-tab-strip');
    makeOverflowing(strip);

    // Siblings in the same row, not absolutely positioned over the tabs
    const back = screen.getByTestId('test-tab-scroll-left');
    expect(back.parentElement).toBe(strip.parentElement);
    expect(back.className).not.toContain('absolute');
  });

  it('scrolls the strip forward when the arrow is clicked', () => {
    render(<Harness tabs={manyTabs} />);
    const strip = screen.getByTestId('test-tab-strip');
    const scrollBy = vi.fn();
    strip.scrollBy = scrollBy;
    makeOverflowing(strip);

    fireEvent.click(screen.getByTestId('test-tab-scroll-right'));

    expect(scrollBy).toHaveBeenCalledTimes(1);
    const [{ left, behavior }] = scrollBy.mock.calls[0];
    expect(left).toBeGreaterThan(0);
    expect(behavior).toBe('smooth');
  });

  it('scrolls back when the other arrow is clicked', () => {
    render(<Harness tabs={manyTabs} />);
    const strip = screen.getByTestId('test-tab-strip');
    const scrollBy = vi.fn();
    strip.scrollBy = scrollBy;
    makeOverflowing(strip, 120);

    fireEvent.click(screen.getByTestId('test-tab-scroll-left'));

    expect(scrollBy.mock.calls[0][0].left).toBeLessThan(0);
  });
});
