import type { LucideIcon } from 'lucide-react';
import { Sparkles, MousePointer2, Move, Menu, PanelRight } from 'lucide-react';

export interface TourStepData {
  id: string;
  /** Short message shown in the tooltip */
  message: string;
  /** data-testid of the target element to anchor the tooltip to */
  targetTestId: string;
  /** Preferred tooltip placement relative to the target */
  placement: 'top' | 'bottom' | 'left' | 'right' | 'center';
  /** Icon shown alongside the message */
  icon: LucideIcon;
}

export const TOUR_STEPS: TourStepData[] = [
  {
    id: 'toolbar',
    message: 'Select tools and add elements to the canvas from here.',
    targetTestId: 'toolbar',
    placement: 'bottom',
    icon: MousePointer2,
  },
  {
    id: 'canvas',
    message: 'Your drawing area — pan, zoom, and place elements here.',
    targetTestId: 'viewport-transform-container',
    placement: 'center',
    icon: Move,
  },
  {
    id: 'menu',
    message: 'Save, load, export, and access settings from this menu.',
    targetTestId: 'hamburger-menu',
    placement: 'bottom',
    icon: Menu,
  },
  {
    id: 'sidebar',
    message: 'Configure selected elements and service properties here.',
    targetTestId: 'sidebar-panel',
    placement: 'left',
    icon: PanelRight,
  },
];

export const TOUR_STEP_COUNT = TOUR_STEPS.length;

// =============================================================================
// DEACTIVATED: Dialog-based tour page data (for future reactivation)
// =============================================================================
// The dialog-based welcome tour (WelcomeDialog.tsx) used this data structure.
// When screenshots are ready, reactivate by:
// 1. Restoring WelcomeDialog.tsx from git history or the _deactivated file
// 2. Uncommenting the TOUR_PAGES export below
// 3. Switching the import in page.tsx from OnboardingTour to WelcomeDialog
// 4. Updating tour-store.ts TOUR_PAGES_COUNT to match TOUR_PAGES.length
//
// export interface TourPageData {
//   id: string;
//   title: string;
//   description: string;
//   icon: LucideIcon;
//   image?: string;
// }
//
// export const TOUR_PAGES: TourPageData[] = [
//   {
//     id: 'welcome',
//     title: 'Welcome to Diagram Editor',
//     icon: Sparkles,
//     image: '/tour-images/site.png',
//     description: 'Design AWS architecture diagrams visually. This quick tour will show you around the main areas of the editor.',
//   },
//   {
//     id: 'toolbar',
//     title: 'The Toolbar',
//     icon: MousePointer2,
//     image: '/tour-images/toolbar.png',
//     description: 'Select tools here to draw on the canvas. Pick a service from the toolbar, then click on the canvas to place it.',
//   },
//   {
//     id: 'canvas',
//     title: 'The Canvas',
//     icon: Move,
//     image: '/tour-images/canvas.png',
//     description: 'Your infinite drawing area. Pan by dragging, zoom with the scroll wheel, and drag elements to reposition them.',
//   },
//   {
//     id: 'menu',
//     title: 'The Menu',
//     icon: Menu,
//     image: '/tour-images/menu.png',
//     description: 'Access save, load, export to Terraform, project settings, and preferences from the hamburger menu.',
//   },
//   {
//     id: 'sidebar',
//     title: 'The Sidebar',
//     icon: PanelRight,
//     image: '/tour-images/sidebar.png',
//     description: 'Configure selected elements here. Set service properties, visual styles, and Terraform variables.',
//   },
// ];
