'use client';

import { useCallback } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useTourStore } from '@/store/tour-store';
import { TOUR_PAGES } from '@/data/tour-pages';

export default function WelcomeDialog() {
  const isActive = useTourStore((s) => s.isActive);
  const currentPage = useTourStore((s) => s.currentPage);
  const nextPage = useTourStore((s) => s.nextPage);
  const prevPage = useTourStore((s) => s.prevPage);
  const completeTour = useTourStore((s) => s.completeTour);

  const page = TOUR_PAGES[currentPage];
  const isFirst = currentPage === 0;
  const isLast = currentPage === TOUR_PAGES.length - 1;

  const handleEscape = useCallback(() => {
    completeTour();
  }, [completeTour]);

  if (!isActive || !page) return null;

  const Icon = page.icon;

  return (
    <Dialog
      open={isActive}
      onOpenChange={(open) => {
        if (!open) completeTour();
      }}
    >
      <DialogContent
        showCloseButton={false}
        className="max-w-[520px]"
        aria-label="Welcome Tour"
        onEscapeKeyDown={handleEscape}
      >
        {/* Tour image or placeholder */}
        {page.image ? (
          <div className="w-full overflow-hidden rounded-md border border-muted-foreground/20">
            <img
              src={page.image}
              alt={page.title}
              className="aspect-video w-full object-cover object-top"
            />
          </div>
        ) : (
          <div className="flex aspect-video w-full items-center justify-center rounded-md border-2 border-dashed border-muted-foreground/30 bg-muted/20">
            <Icon className="size-12 text-muted-foreground/50" />
          </div>
        )}

        <DialogHeader>
          <DialogTitle>{page.title}</DialogTitle>
          <DialogDescription>{page.description}</DialogDescription>
        </DialogHeader>

        {/* Dot pagination indicator */}
        <div className="flex items-center justify-center gap-1.5">
          {TOUR_PAGES.map((_, i) => (
            <span
              key={i}
              className={cn(
                'size-2 rounded-full transition-colors',
                i === currentPage
                  ? 'bg-primary'
                  : 'bg-muted-foreground/30',
              )}
            />
          ))}
        </div>

        <DialogFooter className="flex-row items-center justify-between sm:justify-between">
          <Button variant="ghost" size="sm" onClick={completeTour}>
            Skip
          </Button>
          <div className="flex gap-2">
            {!isFirst && (
              <Button variant="outline" size="sm" onClick={prevPage}>
                Back
              </Button>
            )}
            {isLast ? (
              <Button size="sm" onClick={completeTour}>
                Get Started
              </Button>
            ) : (
              <Button size="sm" onClick={nextPage}>
                Next
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
