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

  it('shows no scroll arrows while every tab fits', () => {
    render(<Harness tabs={twoTabs} />);

    expect(screen.queryByTestId('test-tab-scroll-left')).toBeNull();
    expect(screen.queryByTestId('test-tab-scroll-right')).toBeNull();
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

    expect(screen.getByTestId('test-tab-scroll-right')).toBeDefined();
    // Nothing is scrolled past yet, so there is nothing to go back to
    expect(screen.queryByTestId('test-tab-scroll-left')).toBeNull();
  });

  it('offers a back arrow once the strip has been scrolled', () => {
    render(<Harness tabs={manyTabs} />);

    makeOverflowing(screen.getByTestId('test-tab-strip'), 120);

    expect(screen.getByTestId('test-tab-scroll-left')).toBeDefined();
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
