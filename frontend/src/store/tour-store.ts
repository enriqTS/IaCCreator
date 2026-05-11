import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/** Total number of tour pages. Must match TOUR_PAGES.length in data/tour-pages.ts */
const TOUR_PAGES_COUNT = 5;

export interface TourState {
  /** Whether the welcome dialog is currently visible */
  isActive: boolean;
  /** Whether the user has completed or skipped the tour */
  completed: boolean;
  /** Current page index (0-based) */
  currentPage: number;
  /** Start or restart the tour from page 0 */
  startTour: () => void;
  /** Advance to the next page (clamped to last page index) */
  nextPage: () => void;
  /** Go back to the previous page (clamped to 0) */
  prevPage: () => void;
  /** Complete or skip the tour — sets completed=true, isActive=false */
  completeTour: () => void;
}

export const useTourStore = create<TourState>()(
  persist(
    (set, get) => ({
      isActive: false,
      completed: false,
      currentPage: 0,
      startTour: () => set({ isActive: true, currentPage: 0 }),
      nextPage: () => {
        const { currentPage } = get();
        set({ currentPage: Math.min(currentPage + 1, TOUR_PAGES_COUNT - 1) });
      },
      prevPage: () => {
        const { currentPage } = get();
        set({ currentPage: Math.max(0, currentPage - 1) });
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
            state.currentPage = 0;
          }
          return;
        }
        if (state && !state.completed) {
          // First visit — activate tour after hydration
          state.isActive = true;
          state.currentPage = 0;
        }
      },
    },
  ),
);
