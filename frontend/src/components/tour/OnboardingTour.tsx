'use client';

/**
 * OnboardingTour — Lightweight tooltip-based tour.
 *
 * Shows short messages anchored to the actual UI elements (toolbar, canvas,
 * menu, sidebar) using their data-testid attributes. Steps through each area
 * with Next/Back/Skip controls.
 *
 * This replaces the dialog-based WelcomeDialog approach. To reactivate the
 * dialog version (with screenshots), see the comments in data/tour-pages.ts.
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useTourStore } from '@/store/tour-store';
import { TOUR_STEPS } from '@/data/tour-pages';

interface TooltipPosition {
  top: number;
  left: number;
}

function computePosition(
  targetRect: DOMRect,
  placement: 'top' | 'bottom' | 'left' | 'right',
  tooltipWidth: number,
  tooltipHeight: number,
): TooltipPosition {
  const gap = 12;

  switch (placement) {
    case 'bottom':
      return {
        top: targetRect.bottom + gap,
        left: targetRect.left + targetRect.width / 2 - tooltipWidth / 2,
      };
    case 'top':
      return {
        top: targetRect.top - tooltipHeight - gap,
        left: targetRect.left + targetRect.width / 2 - tooltipWidth / 2,
      };
    case 'left':
      return {
        top: targetRect.top + targetRect.height / 2 - tooltipHeight / 2,
        left: targetRect.left - tooltipWidth - gap,
      };
    case 'right':
      return {
        top: targetRect.top + targetRect.height / 2 - tooltipHeight / 2,
        left: targetRect.right + gap,
      };
  }
}

function clampToViewport(pos: TooltipPosition, width: number, height: number): TooltipPosition {
  const padding = 12;
  return {
    top: Math.max(padding, Math.min(pos.top, window.innerHeight - height - padding)),
    left: Math.max(padding, Math.min(pos.left, window.innerWidth - width - padding)),
  };
}

export default function OnboardingTour() {
  const isActive = useTourStore((s) => s.isActive);
  const currentStep = useTourStore((s) => s.currentStep);
  const nextStep = useTourStore((s) => s.nextStep);
  const prevStep = useTourStore((s) => s.prevStep);
  const completeTour = useTourStore((s) => s.completeTour);

  const [position, setPosition] = useState<TooltipPosition>({ top: 0, left: 0 });
  const [visible, setVisible] = useState(false);
  const tooltipRef = useRef<HTMLDivElement>(null);

  const step = TOUR_STEPS[currentStep];
  const isFirst = currentStep === 0;
  const isLast = currentStep === TOUR_STEPS.length - 1;

  const updatePosition = useCallback(() => {
    if (!step) return;

    const target = document.querySelector(`[data-testid="${step.targetTestId}"]`);
    if (!target) {
      // Fallback: center of viewport
      setPosition({
        top: window.innerHeight / 2 - 40,
        left: window.innerWidth / 2 - 140,
      });
      setVisible(true);
      return;
    }

    const targetRect = target.getBoundingClientRect();
    // Estimate tooltip size (will refine after render)
    const tooltipWidth = 280;
    const tooltipHeight = 100;

    const raw = computePosition(targetRect, step.placement, tooltipWidth, tooltipHeight);
    const clamped = clampToViewport(raw, tooltipWidth, tooltipHeight);
    setPosition(clamped);
    setVisible(true);
  }, [step]);

  // Recompute position when step changes or window resizes
  useEffect(() => {
    if (!isActive) {
      setVisible(false);
      return;
    }

    // Small delay to let layout settle
    const timer = setTimeout(updatePosition, 50);
    window.addEventListener('resize', updatePosition);

    return () => {
      clearTimeout(timer);
      window.removeEventListener('resize', updatePosition);
    };
  }, [isActive, currentStep, updatePosition]);

  // Escape key to dismiss
  useEffect(() => {
    if (!isActive) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.stopPropagation();
        e.preventDefault();
        completeTour();
      }
    }

    window.addEventListener('keydown', handleKeyDown, true);
    return () => window.removeEventListener('keydown', handleKeyDown, true);
  }, [isActive, completeTour]);

  if (!isActive || !step) return null;

  const Icon = step.icon;

  const tooltip = (
    <div
      ref={tooltipRef}
      role="dialog"
      aria-label="Onboarding Tour"
      data-testid="onboarding-tour-tooltip"
      className={cn(
        'fixed z-[9999] w-[280px] rounded-lg border border-border bg-popover p-4 shadow-lg transition-opacity duration-200',
        visible ? 'opacity-100' : 'opacity-0',
      )}
      style={{ top: position.top, left: position.left }}
    >
      {/* Message */}
      <div className="mb-3 flex items-start gap-2">
        <Icon className="mt-0.5 size-4 shrink-0 text-primary" />
        <p className="text-sm text-popover-foreground">{step.message}</p>
      </div>

      {/* Dot indicators */}
      <div className="mb-3 flex items-center justify-center gap-1.5">
        {TOUR_STEPS.map((_, i) => (
          <span
            key={i}
            className={cn(
              'size-1.5 rounded-full transition-colors',
              i === currentStep ? 'bg-primary' : 'bg-muted-foreground/30',
            )}
          />
        ))}
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-xs text-muted-foreground"
          onClick={completeTour}
        >
          Skip
        </Button>
        <div className="flex gap-1.5">
          {!isFirst && (
            <Button variant="outline" size="sm" className="h-7 px-2 text-xs" onClick={prevStep}>
              Back
            </Button>
          )}
          {isLast ? (
            <Button size="sm" className="h-7 px-3 text-xs" onClick={completeTour}>
              Done
            </Button>
          ) : (
            <Button size="sm" className="h-7 px-3 text-xs" onClick={nextStep}>
              Next
            </Button>
          )}
        </div>
      </div>
    </div>
  );

  return createPortal(tooltip, document.body);
}
