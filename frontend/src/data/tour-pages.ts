import type { LucideIcon } from 'lucide-react';
import { Sparkles, MousePointer2, Move, Menu, PanelRight } from 'lucide-react';

export interface TourPageData {
  id: string;
  title: string;
  description: string;
  icon: LucideIcon;
  /** Path to screenshot image in /public. When set, replaces the placeholder icon. */
  image?: string;
}

export const TOUR_PAGES: TourPageData[] = [
  {
    id: 'welcome',
    title: 'Welcome to Diagram Editor',
    icon: Sparkles,
    image: '/tour-images/site.png',
    description:
      'Design AWS architecture diagrams visually. This quick tour will show you around the main areas of the editor.',
  },
  {
    id: 'toolbar',
    title: 'The Toolbar',
    icon: MousePointer2,
    image: '/tour-images/toolbar.png',
    description:
      'Select tools here to draw on the canvas. Pick a service from the toolbar, then click on the canvas to place it.',
  },
  {
    id: 'canvas',
    title: 'The Canvas',
    icon: Move,
    image: '/tour-images/canvas.png',
    description:
      'Your infinite drawing area. Pan by dragging, zoom with the scroll wheel, and drag elements to reposition them.',
  },
  {
    id: 'menu',
    title: 'The Menu',
    icon: Menu,
    image: '/tour-images/menu.png',
    description:
      'Access save, load, export to Terraform, project settings, and preferences from the hamburger menu.',
  },
  {
    id: 'sidebar',
    title: 'The Sidebar',
    icon: PanelRight,
    image: '/tour-images/sidebar.png',
    description:
      'Configure selected elements here. Set service properties, visual styles, and Terraform variables.',
  },
];

export const TOUR_PAGE_COUNT = TOUR_PAGES.length;
