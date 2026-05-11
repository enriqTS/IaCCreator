import type { LucideIcon } from 'lucide-react';
import { Sparkles, MousePointer2, Move, Menu, PanelRight } from 'lucide-react';

export interface TourPageData {
  id: string;
  title: string;
  description: string;
  icon: LucideIcon;
}

export const TOUR_PAGES: TourPageData[] = [
  {
    id: 'welcome',
    title: 'Welcome to Diagram Editor',
    icon: Sparkles,
    description:
      'Design AWS architecture diagrams visually. This quick tour will show you around the main areas of the editor.',
  },
  {
    id: 'toolbar',
    title: 'The Toolbar',
    icon: MousePointer2,
    description:
      'Select tools here to draw on the canvas. Pick a service from the toolbar, then click on the canvas to place it.',
  },
  {
    id: 'canvas',
    title: 'The Canvas',
    icon: Move,
    description:
      'Your infinite drawing area. Pan by dragging, zoom with the scroll wheel, and drag elements to reposition them.',
  },
  {
    id: 'menu',
    title: 'The Menu',
    icon: Menu,
    description:
      'Access save, load, export to Terraform, project settings, and preferences from the hamburger menu.',
  },
  {
    id: 'sidebar',
    title: 'The Sidebar',
    icon: PanelRight,
    description:
      'Configure selected elements here. Set service properties, visual styles, and Terraform variables.',
  },
];

export const TOUR_PAGE_COUNT = TOUR_PAGES.length;
