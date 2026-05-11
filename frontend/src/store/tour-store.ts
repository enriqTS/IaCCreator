import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { TOUR_STEP_COUNT } from '@/data/tour-pages';

export interface TourState {
  /** Whether the tour is currently visible */
  isActive: boolean;
  /** Whether the user has completed or skipped the tour */
  completed: boolean;
  /** Current step index (0-based) */
  currentStep: number;
  /** Start or restart the tour from step 0 */
  startTour: () => void;
  /** Advance to the next step (clamped to last step index) */
  nextStep: () => void;
  /** Go back to the previous step (clamped to 0) */
  prevStep: () => void;
  /** Complete or skip the tour — sets completed=true, isActive=false */
  completeTour: () => void;
}

export const useTourStore = create<TourState>()(
  persist(
    (set, get) => ({
      isActive: false,
      completed: false,
      currentStep: 0,
      startTour: () => set({ isActive: true, currentStep: 0 }),
      nextStep: () => {
        const { currentStep } = get();
        set({ currentStep: Math.min(currentStep + 1, TOUR_STEP_COUNT - 1) });
      },
      prevStep: () => {
        const { currentStep } = get();
        set({ currentStep: Math.max(0, currentStep - 1) });
      },
      completeTour: () => set({ isActive: false, completed: true }),
    }),
    {
      name: 'diagram-editor:tour-state',
      partialize: (state) => ({ completed: state.completed }),
      onRehydrateStorage: () => (state, error) => {
        if (error) {
          // localStorage unavailable or corrupted — treat as first visit
          console.warn(
            '[tour-store] Failed to hydrate tour state from localStorage:',
            error,
          );
          if (state) {
            state.isActive = true;
            state.currentStep = 0;
          }
          return;
        }
        if (state && !state.completed) {
          // First visit — activate tour after hydration
          state.isActive = true;
          state.currentStep = 0;
        }
      },
    },
  ),
);
