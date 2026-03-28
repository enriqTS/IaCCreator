/**
 * Inline SVG icons for geometric shapes, UML elements, text, and lines.
 * Used in the ObjectPickerMenu icon grid for non-AWS items.
 */

const S = 24; // viewBox size
const C = '#e5e5e5'; // stroke color
const W = 1.5; // stroke width

/** Returns an inline SVG element for the given item name, or null if not mapped. */
export function getItemIcon(name: string): React.ReactElement | null {
  const icon = ICON_MAP[name];
  return icon ?? null;
}

const ICON_MAP: Record<string, React.ReactElement> = {
  // --- Geometric Shapes ---
  'Rectangle': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><rect x="3" y="5" width="18" height="14" rx="0" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Rounded Rectangle': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><rect x="3" y="5" width="18" height="14" rx="4" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Ellipse': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><ellipse cx="12" cy="12" rx="9" ry="7" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Circle': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><circle cx="12" cy="12" r="8" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Triangle': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><polygon points="12,3 22,21 2,21" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Diamond': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><polygon points="12,2 22,12 12,22 2,12" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Parallelogram': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><polygon points="6,19 2,5 18,5 22,19" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Trapezoid': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><polygon points="5,19 1,5 23,5 19,19" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Hexagon': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><polygon points="6,2 18,2 23,12 18,22 6,22 1,12" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Octagon': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><polygon points="8,2 16,2 22,8 22,16 16,22 8,22 2,16 2,8" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Pentagon': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><polygon points="12,2 22,9 19,21 5,21 2,9" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Star': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><polygon points="12,2 14.5,9 22,9 16,14 18,21 12,17 6,21 8,14 2,9 9.5,9" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Cross': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><polygon points="8,2 16,2 16,8 22,8 22,16 16,16 16,22 8,22 8,16 2,16 2,8 8,8" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Arrow Right': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><polygon points="2,8 16,8 16,3 22,12 16,21 16,16 2,16" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Arrow Left': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><polygon points="22,8 8,8 8,3 2,12 8,21 8,16 22,16" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Arrow Up': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><polygon points="8,22 8,8 3,8 12,2 21,8 16,8 16,22" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Arrow Down': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><polygon points="8,2 8,16 3,16 12,22 21,16 16,16 16,2" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Chevron': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><polygon points="2,4 16,4 22,12 16,20 2,20 8,12" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Cylinder': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}>
      <ellipse cx="12" cy="6" rx="8" ry="3" fill="none" stroke={C} strokeWidth={W}/>
      <line x1="4" y1="6" x2="4" y2="18" stroke={C} strokeWidth={W}/>
      <line x1="20" y1="6" x2="20" y2="18" stroke={C} strokeWidth={W}/>
      <ellipse cx="12" cy="18" rx="8" ry="3" fill="none" stroke={C} strokeWidth={W}/>
    </svg>
  ),
  'Cloud': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><path d="M6,18 C2,18 1,14 3,12 C1,9 4,6 7,7 C8,4 13,3 15,6 C18,4 22,6 21,10 C23,11 23,15 20,16 C21,18 18,20 15,18 Z" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Callout': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}>
      <rect x="2" y="2" width="20" height="14" rx="2" fill="none" stroke={C} strokeWidth={W}/>
      <polygon points="6,16 10,16 4,22" fill="none" stroke={C} strokeWidth={W}/>
    </svg>
  ),
  'Document': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><path d="M4,2 L20,2 L20,19 C16,22 8,16 4,19 Z" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Process': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><rect x="3" y="5" width="18" height="14" rx="0" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Decision': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><polygon points="12,2 22,12 12,22 2,12" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Data': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><polygon points="6,4 22,4 18,20 2,20" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Predefined Process': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}>
      <rect x="3" y="5" width="18" height="14" fill="none" stroke={C} strokeWidth={W}/>
      <line x1="6" y1="5" x2="6" y2="19" stroke={C} strokeWidth={W}/>
      <line x1="18" y1="5" x2="18" y2="19" stroke={C} strokeWidth={W}/>
    </svg>
  ),

  // --- UML Elements ---
  'Class': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}>
      <rect x="3" y="2" width="18" height="20" fill="none" stroke={C} strokeWidth={W}/>
      <line x1="3" y1="8" x2="21" y2="8" stroke={C} strokeWidth={W}/>
      <line x1="3" y1="14" x2="21" y2="14" stroke={C} strokeWidth={W}/>
    </svg>
  ),
  'Interface': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}>
      <circle cx="12" cy="8" r="4" fill="none" stroke={C} strokeWidth={W}/>
      <line x1="12" y1="12" x2="12" y2="22" stroke={C} strokeWidth={W}/>
    </svg>
  ),
  'Actor': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}>
      <circle cx="12" cy="5" r="3" fill="none" stroke={C} strokeWidth={W}/>
      <line x1="12" y1="8" x2="12" y2="16" stroke={C} strokeWidth={W}/>
      <line x1="5" y1="12" x2="19" y2="12" stroke={C} strokeWidth={W}/>
      <line x1="12" y1="16" x2="6" y2="22" stroke={C} strokeWidth={W}/>
      <line x1="12" y1="16" x2="18" y2="22" stroke={C} strokeWidth={W}/>
    </svg>
  ),
  'Use Case': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><ellipse cx="12" cy="12" rx="10" ry="7" fill="none" stroke={C} strokeWidth={W}/></svg>
  ),
  'Component': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}>
      <rect x="6" y="2" width="16" height="20" fill="none" stroke={C} strokeWidth={W}/>
      <rect x="2" y="6" width="6" height="4" fill="none" stroke={C} strokeWidth={W}/>
      <rect x="2" y="14" width="6" height="4" fill="none" stroke={C} strokeWidth={W}/>
    </svg>
  ),
  'Package': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}>
      <rect x="2" y="6" width="20" height="16" fill="none" stroke={C} strokeWidth={W}/>
      <rect x="2" y="2" width="10" height="4" fill="none" stroke={C} strokeWidth={W}/>
    </svg>
  ),
  'Node': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}>
      <polygon points="2,8 2,22 18,22 18,8" fill="none" stroke={C} strokeWidth={W}/>
      <polygon points="2,8 6,2 22,2 18,8" fill="none" stroke={C} strokeWidth={W}/>
      <polygon points="18,8 22,2 22,16 18,22" fill="none" stroke={C} strokeWidth={W}/>
    </svg>
  ),

  // --- Text & Lines ---
  'Text': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}>
      <line x1="4" y1="4" x2="20" y2="4" stroke={C} strokeWidth={W}/>
      <line x1="12" y1="4" x2="12" y2="20" stroke={C} strokeWidth={W}/>
      <line x1="8" y1="20" x2="16" y2="20" stroke={C} strokeWidth={W}/>
    </svg>
  ),
  'Line': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}><line x1="3" y1="21" x2="21" y2="3" stroke={C} strokeWidth={W}/></svg>
  ),
  'Arrow': (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`}>
      <line x1="3" y1="21" x2="21" y2="3" stroke={C} strokeWidth={W}/>
      <polyline points="14,3 21,3 21,10" fill="none" stroke={C} strokeWidth={W}/>
    </svg>
  ),
};
