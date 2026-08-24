'use client';

import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ConfigTab {
  id: string;
  label: string;
  content: ReactNode;
}

interface ConfigTabsProps {
  tabs: ConfigTab[];
  value: string;
  onValueChange: (id: string) => void;
  /** Prefix for the strip and trigger test ids, so panels stay distinguishable. */
  testIdPrefix?: string;
  className?: string;
}

/** How much of the strip one arrow click travels. */
const SCROLL_FRACTION = 0.7;

/** The shared tabbed layout every configuration panel uses. */
export default function ConfigTabs({
  tabs,
  value,
  onValueChange,
  testIdPrefix = 'config',
  className,
}: ConfigTabsProps) {
  const stripRef = useRef<HTMLDivElement>(null);
  const [canScroll, setCanScroll] = useState({ left: false, right: false });

  const syncArrows = useCallback(() => {
    const strip = stripRef.current;
    if (!strip) return;
    setCanScroll({
      left: strip.scrollLeft > 1,
      right: strip.scrollLeft + strip.clientWidth < strip.scrollWidth - 1,
    });
  }, []);

  useEffect(() => {
    syncArrows();
    const strip = stripRef.current;
    // jsdom has no ResizeObserver, and the arrows are not what tests assert on
    if (!strip || typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(syncArrows);
    observer.observe(strip);
    return () => observer.disconnect();
  }, [syncArrows, tabs]);

  const scrollBy = useCallback((direction: -1 | 1) => {
    const strip = stripRef.current;
    if (!strip) return;
    const distance = strip.clientWidth * SCROLL_FRACTION * direction;
    if (typeof strip.scrollBy === 'function') {
      strip.scrollBy({ left: distance, behavior: 'smooth' });
    } else {
      strip.scrollLeft += distance;
    }
  }, []);

  const effectiveTab = tabs.some((tab) => tab.id === value) ? value : tabs[0]?.id ?? '';

  return (
    <Tabs
      value={effectiveTab}
      onValueChange={onValueChange}
      className={cn('w-full min-w-0', className)}
    >
      <div className="relative min-w-0">
        <div
          ref={stripRef}
          data-testid={`${testIdPrefix}-tab-strip`}
          onScroll={syncArrows}
          // overflow-y must be stated: leaving it visible makes CSS compute it to auto,
          // which would let the strip scroll vertically as well as across
          className="overflow-x-auto overflow-y-hidden [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        >
          {/* Tabs keep their natural width so the next one stays partly visible as a hint */}
          <TabsList data-testid={`${testIdPrefix}-tab-bar`} className="w-max">
            {tabs.map((tab) => (
              <TabsTrigger
                key={tab.id}
                value={tab.id}
                data-testid={`${testIdPrefix}-tab-${tab.id.toLowerCase()}`}
                className="flex-none px-3 text-xs"
              >
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>

        {canScroll.left && (
          <ScrollArrow side="left" testIdPrefix={testIdPrefix} onClick={() => scrollBy(-1)} />
        )}
        {canScroll.right && (
          <ScrollArrow side="right" testIdPrefix={testIdPrefix} onClick={() => scrollBy(1)} />
        )}
      </div>

      {tabs.map((tab) => (
        <TabsContent key={tab.id} value={tab.id} data-testid={`${testIdPrefix}-panel-${tab.id.toLowerCase()}`}>
          {tab.content}
        </TabsContent>
      ))}
    </Tabs>
  );
}

/** An edge arrow standing in for the hidden scrollbar. */
function ScrollArrow({
  side,
  testIdPrefix,
  onClick,
}: {
  side: 'left' | 'right';
  testIdPrefix: string;
  onClick: () => void;
}) {
  const Icon = side === 'left' ? ChevronLeft : ChevronRight;
  return (
    <div
      className={cn(
        'pointer-events-none absolute inset-y-0 flex items-center',
        side === 'left'
          ? 'left-0 bg-gradient-to-r from-background to-transparent pr-4'
          : 'right-0 bg-gradient-to-l from-background to-transparent pl-4',
      )}
    >
      <Button
        variant="ghost"
        size="icon-xs"
        data-testid={`${testIdPrefix}-tab-scroll-${side}`}
        aria-label={`Scroll tabs ${side}`}
        onClick={onClick}
        className="pointer-events-auto"
      >
        <Icon />
      </Button>
    </div>
  );
}
