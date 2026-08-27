import { AWS_ICON_REGISTRY } from '@/data/aws-icon-registry';
import type { GeometricShape, UMLKind, Tool } from '@/types/diagram';

export interface PickerItem {
  name: string;
  category: string;
  icon?: string;
  tool: Tool;
}

const GEOMETRIC_SHAPES: { name: string; shape: GeometricShape }[] = [
  { name: 'Rectangle', shape: 'rectangle' },
  { name: 'Rounded Rectangle', shape: 'rounded-rectangle' },
  { name: 'Ellipse', shape: 'ellipse' },
  { name: 'Circle', shape: 'circle' },
  { name: 'Triangle', shape: 'triangle' },
  { name: 'Diamond', shape: 'diamond' },
  { name: 'Parallelogram', shape: 'parallelogram' },
  { name: 'Trapezoid', shape: 'trapezoid' },
  { name: 'Hexagon', shape: 'hexagon' },
  { name: 'Octagon', shape: 'octagon' },
  { name: 'Pentagon', shape: 'pentagon' },
  { name: 'Star', shape: 'star' },
  { name: 'Cross', shape: 'cross' },
  { name: 'Arrow Right', shape: 'arrow-right' },
  { name: 'Arrow Left', shape: 'arrow-left' },
  { name: 'Arrow Up', shape: 'arrow-up' },
  { name: 'Arrow Down', shape: 'arrow-down' },
  { name: 'Chevron', shape: 'chevron' },
  { name: 'Cylinder', shape: 'cylinder' },
  { name: 'Cloud', shape: 'cloud' },
  { name: 'Callout', shape: 'callout' },
  { name: 'Document', shape: 'document' },
  { name: 'Process', shape: 'process' },
  { name: 'Decision', shape: 'decision' },
  { name: 'Data', shape: 'data' },
  { name: 'Predefined Process', shape: 'predefined-process' },
];

const UML_ELEMENTS: { name: string; kind: UMLKind }[] = [
  { name: 'Class', kind: 'class' },
  { name: 'Interface', kind: 'interface' },
  { name: 'Actor', kind: 'actor' },
  { name: 'Use Case', kind: 'use-case' },
  { name: 'Component', kind: 'component' },
  { name: 'Package', kind: 'package' },
  { name: 'Node', kind: 'node' },
];

export interface PickerCategory {
  category: string;
  items: PickerItem[];
}

function buildAllPickerItems(): PickerCategory[] {
  const categories: PickerCategory[] = [
    {
      category: 'Architecture Scopes',
      items: [
        { name: 'AWS Region', category: 'Architecture Scopes', tool: { type: 'place-semantic-container', containerType: 'region' } },
        { name: 'Availability Zone', category: 'Architecture Scopes', tool: { type: 'place-semantic-container', containerType: 'availability-zone' } },
        { name: 'Generic Boundary', category: 'Architecture Scopes', tool: { type: 'place-semantic-container', containerType: 'generic' } },
      ],
    },
  ];

  for (const cat of AWS_ICON_REGISTRY) {
    const items: PickerItem[] = cat.services.map((svc) => ({
      name: svc.name,
      category: `AWS: ${cat.name}`,
      icon: svc.iconPath,
      // Null service types are explicitly decorative and cannot be placed.
      tool: svc.serviceType
        ? ({ type: 'place-service', serviceType: svc.serviceType } as Tool)
        : ('pointer' as Tool),
    }));
    categories.push({ category: `AWS: ${cat.name}`, items });
  }

  categories.push({
    category: 'Shapes',
    items: GEOMETRIC_SHAPES.map((s) => ({
      name: s.name,
      category: 'Shapes',
      tool: { type: 'place-shape', shape: s.shape } as Tool,
    })),
  });

  categories.push({
    category: 'UML',
    items: UML_ELEMENTS.map((u) => ({
      name: u.name,
      category: 'UML',
      tool: { type: 'place-uml', umlKind: u.kind } as Tool,
    })),
  });

  categories.push({
    category: 'Text',
    items: [{ name: 'Text', category: 'Text', tool: 'text' as Tool }],
  });

  categories.push({
    category: 'Lines & Arrows',
    items: [
      { name: 'Line', category: 'Lines & Arrows', tool: { type: 'place-line' } as Tool },
      { name: 'Arrow', category: 'Lines & Arrows', tool: { type: 'place-arrow' } as Tool },
    ],
  });

  return categories;
}

export const ALL_CATEGORIES: PickerCategory[] = buildAllPickerItems();

export const ALL_ITEMS: PickerItem[] = ALL_CATEGORIES.flatMap((c) => c.items);

export const ALL_CATEGORY_NAMES: string[] = ALL_CATEGORIES.map((c) => c.category);

const AWS_CATEGORY_PREFIX = 'AWS: ';

// The prefix repeats on every AWS category and only costs width in a narrow panel
export function categoryLabel(category: string): string {
  return category.startsWith(AWS_CATEGORY_PREFIX)
    ? category.slice(AWS_CATEGORY_PREFIX.length)
    : category;
}

export function toolsMatch(a: Tool, b: Tool): boolean {
  if (typeof a === 'string' || typeof b === 'string') return a === b;
  if (a.type !== b.type) return false;
  return JSON.stringify(a) === JSON.stringify(b);
}

// Resolves an armed placement tool back to the catalog entry it came from
export function findItemForTool(tool: Tool): PickerItem | null {
  if (tool === 'pointer') return null;
  return ALL_ITEMS.find((item) => toolsMatch(item.tool, tool)) ?? null;
}

export function isAwsServiceItem(item: PickerItem): boolean {
  return typeof item.tool === 'object' && 'type' in item.tool && item.tool.type === 'place-service';
}

export function isUnsupportedAwsItem(item: PickerItem): boolean {
  return item.category.startsWith('AWS:') && !isAwsServiceItem(item);
}
