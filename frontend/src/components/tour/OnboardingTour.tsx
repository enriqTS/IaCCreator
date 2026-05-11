'use client';

/**
 * OnboardingTour — Lightweight tooltip-based tour.
 *
 * Shows short messages anchored to the actual UI elements (toolbar, canvas,
 * menu, sidebar) using their data-testid attributes. Steps through each area
 * with Next/Back/Skip controls.
 *
 * Each step renders a fresh tooltip instance (via React key) so there's no
 * flash of content at the old position when navigating between steps.
 *
 * This replaces the dialog-based WelcomeDialog approach. To reactivate the
 * dialog version (with screenshots), see the comments in data/tour-pages.ts.
 */

import { useEffect, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useTourStore } from '@/store/tour-store';
import { TOUR_STEPS, type TourStepData } from '@/data/tour-pages';

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

function getTargetInfo(step: TourStepData): { testId: string; placement: 'top' | 'bottom' | 'left' | 'right' } {
  if (step.id === 'sidebar') {
    const expandedPanel = document.querySelector('[data-testid="sidebar-panel"]');
    if (!expandedPanel) {
      return { testId: 'sidebar-toggle-collapsed', placement: 'left' };
    }
  }
  return { testId: step.targetTestId, placement: step.placement };
}

// ─── Individual tooltip instance (keyed per step, so it mounts fresh) ────────

interface StepTooltipProps {
  step: TourStepData;
  stepIndex: number;
  totalSteps: number;
  isFirst: boolean;
  isLast: boolean;
  onNext: () => void;
  onPrev: () => void;
  onComplete: () => void;
}

function StepTooltip({ step, stepIndex, totalSteps, isFirst, isLast, onNext, onPrev, onComplete }: StepTooltipProps) {
  const [position, setPosition] = useState<TooltipPosition | null>(null);

  const updatePosition = useCallback(() => {
    const { testId, placement } = getTargetInfo(step);
    const target = document.querySelector(`[data-testid="${testId}"]`);

    if (!target) {
      setPosition({
        top: window.innerHeight / 2 - 50,
        left: window.innerWidth / 2 - 140,
      });
      return;
    }

    const targetRect = target.getBoundingClientRect();
    const tooltipWidth = 280;
    const tooltipHeight = 120;

    const raw = computePosition(targetRect, placement, tooltipWidth, tooltipHeight);
    const clamped = clampToViewport(raw, tooltipWidth, tooltipHeight);
    setPosition(clamped);
  }, [step]);

  useEffect(() => {
    // Compute position immediately on mount
    updatePosition();
    window.addEventListener('resize', updatePosition);
    return () => window.removeEventListener('resize', updatePosition);
  }, [updatePosition]);

  // Don't render until position is computed
  if (!position) return null;

  const Icon = step.icon;

  return (
    <div
      role="dialog"
      aria-label="Onboarding Tour"
      data-testid="onboarding-tour-tooltip"
      className="fixed z-[9999] w-[280px] rounded-lg border border-border bg-popover p-4 shadow-lg"
      style={{ top: position.top, left: position.left }}
    >
      {/* Message */}
      <div className="mb-3 flex items-start gap-2">
        <Icon className="mt-0.5 size-4 shrink-0 text-primary" />
        <p className="text-sm text-popover-foreground">{step.message}</p>
      </div>

      {/* Dot indicators */}
      <div className="mb-3 flex items-center justify-center gap-1.5">
        {Array.from({ length: totalSteps }, (_, i) => (
          <span
            key={i}
            className={cn(
              'size-1.5 rounded-full',
              i === stepIndex ? 'bg-primary' : 'bg-muted-foreground/30',
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
          onClick={onComplete}
        >
          Skip
        </Button>
        <div className="flex gap-1.5">
          {!isFirst && (
            <Button variant="outline" size="sm" className="h-7 px-2 text-xs" onClick={onPrev}>
              Back
            </Button>
          )}
          {isLast ? (
            <Button size="sm" className="h-7 px-3 text-xs" onClick={onComplete}>
              Done
            </Button>
          ) : (
            <Button size="sm" className="h-7 px-3 text-xs" onClick={onNext}>
              Next
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Main tour controller ────────────────────────────────────────────────────

export default function OnboardingTour() {
  const isActive = useTourStore((s) => s.isActive);
  const currentStep = useTourStore((s) => s.currentStep);
  const nextStep = useTourStore((s) => s.nextStep);
  const prevStep = useTourStore((s) => s.prevStep);
  const completeTour = useTourStore((s) => s.completeTour);

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

  const step = TOUR_STEPS[currentStep];
  if (!isActive || !step) return null;

  // Key forces React to unmount the old tooltip and mount a new one at the correct position
  return createPortal(
    <StepTooltip
      key={`tour-step-${currentStep}`}
      step={step}
      stepIndex={currentStep}
      totalSteps={TOUR_STEPS.length}
      isFirst={currentStep === 0}
      isLast={currentStep === TOUR_STEPS.length - 1}
      onNext={nextStep}
      onPrev={prevStep}
      onComplete={completeTour}
    />,
    document.body,
  );
}
