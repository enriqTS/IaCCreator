# Implementation Plan: Canvas Interaction Tests and Remaining Lint

## Overview

Two independent items left over after the hook-rules refactor:

1. **Canvas interaction behaviour has no test coverage**, including code that
   refactor changed. This is the one with real risk.
2. **18 ESLint warnings** remain. None affect correctness; three are debris left
   by a script from the previous session.

Neither blocks anything. Item 1 should be done first, because it protects work
already shipped.

Current state at the time of writing: 0 TypeScript errors, 0 ESLint errors,
806 backend tests and 1283 frontend tests passing.

---

## Part 1: Canvas Interaction Test Coverage

### Why this exists

The hook-rules refactor changed how drag previews and tool-change resets work:

- Drag previews moved from a ref read during render into state
  (`lineDragPreview`, `arrowDragPreview` in `Canvas.tsx`).
- Tool-change resets moved from an effect into a render-time adjustment, split so
  that state resets during render and bookkeeping refs reset in an effect. This
  pattern is now in `Canvas.tsx`, `DragSizingOverlay.tsx`, `MarqueeSelection.tsx`,
  `PlacementPreview.tsx` and `SidebarPanel.tsx`.

Those changes were made behaviour-preserving by construction — the same
conditions performing the same resets, only relocated — because there was nothing
to verify them against. `place-line` and `place-arrow` have **zero** tests, and
`MarqueeSelection` is referenced by no test file at all.

### Current state

| Component | Test file | Covered |
| --- | --- | --- |
| `DragSizingOverlay` | `__tests__/unit/drag-sizing-overlay.test.tsx` | drag sizing, thresholds, min dimensions |
| `PlacementPreview` | `__tests__/unit/placement-preview.test.tsx` | visibility per tool, Escape, icon |
| `MarqueeSelection` | none | nothing |
| `Canvas` drag placement | none | nothing |
| Tool-change resets | none | nothing |

`drag-sizing-overlay.test.tsx` is the model to copy: it renders the component,
drives `mousedown`/`mousemove`/`mouseup` on the container, and asserts on
`data-testid` elements. Follow its structure rather than inventing another.

### Seams available

Every element these tests need already carries a test id, so no source changes
are required to make this testable:

| Test id | Where |
| --- | --- |
| `line-drag-preview-svg` | `Canvas.tsx` — the `place-line` drag preview |
| `arrow-drag-preview-svg` | `Canvas.tsx` — the `place-arrow` drag preview |
| `line-preview-svg` | `Canvas.tsx` — the click-to-click `line` tool preview |
| `viewport-transform-container` | `Canvas.tsx` — the element to dispatch pointer events at |
| `marquee-selection-rect` | `MarqueeSelection.tsx` |
| `drag-sizing-rect` | `DragSizingOverlay.tsx` |
| `placement-preview` | `PlacementPreview.tsx` |
| `tab-bar`, `variables-tab-content` | `SidebarPanel.tsx` |

### Phase 1 — Drag placement

**Goal:** cover `place-line` and `place-arrow`, which have no tests at all and
whose preview state was just rewritten.

For each of the two tools:

- Pressing on the canvas starts a preview whose start and end are the press point.
- Moving extends the preview end while the start stays put. This is the specific
  thing the refactor changed, and the one worth asserting most precisely.
- Releasing creates the line or arrow object in the store, with the endpoints the
  drag described.
- Releasing without moving does not leave a stray preview behind.
- With snap-to-grid on, the start point is snapped; with `altKey` held, it is not.

### Phase 2 — Tool-change resets

**Goal:** pin the behaviour that moved from effects into render-time adjustment.
Assert the visible outcome, not the mechanism, so the tests survive another
refactor of the same code.

- Switching away from `place-line` mid-drag clears `line-drag-preview-svg`;
  same for `place-arrow` and `arrow-drag-preview-svg`.
- Switching away from `line` mid-placement clears `line-preview-svg`.
- Switching away from `pointer` mid-marquee clears `marquee-selection-rect`.
- Switching away from a placement tool mid-drag clears `drag-sizing-rect`.
- Leaving `place-service` clears `placement-preview`.
- Returning to a tool afterwards starts clean — no stale preview from the
  abandoned gesture. This is the case the removed ref resets used to guard, and
  the most likely regression.

### Phase 3 — Sidebar tab reset

**Goal:** cover the one non-canvas component that took the same change.

- Selecting a different object returns the sidebar to its first tab.
- Selecting an object whose tab set does not include the active tab falls back to
  the first available tab.

### Phase 4 — Marquee selection

**Goal:** first coverage for a component that has none.

- Dragging on empty canvas with the pointer tool draws `marquee-selection-rect`.
- Releasing selects the objects the rectangle intersects and leaves objects
  outside it unselected.
- A click without movement does not draw a rectangle and clears the selection.

### Notes

`jsdom` does not implement layout, so anything reading `getBoundingClientRect`
returns zeros unless stubbed. `drag-sizing-overlay.test.tsx` already deals with
this — copy how it does it rather than working it out again. Radix `Select`
also needs `Element.prototype.scrollIntoView` stubbed; see
`__tests__/unit/route-methods-editor.test.tsx`.

---

## Part 2: The Remaining 18 Warnings

Run `corepack pnpm eslint src __tests__` from `frontend/` to see the current list.

### 8 × `@typescript-eslint/no-unused-vars` — dead test bindings

Straight deletions. A pruning script in the previous session patched 17 of 24
files and left these:

| File | Line | Binding |
| --- | --- | --- |
| `__tests__/unit/diagram-store.test.ts` | 3 | `ArchitectureBlock` |
| `__tests__/unit/element-layer.test.tsx` | 36 | `makeLine` |
| `__tests__/unit/export.test.ts` | 2 | `ExportResult` |
| `__tests__/unit/fixed-connection-routing.test.ts` | 5 | `DEFAULT_LINE_VISUAL` |
| `__tests__/unit/global-terraform-config-panel.test.tsx` | 203 | `container` |
| `__tests__/unit/multi-select-field-renderer.test.ts` | 2 | `SchemaField` |
| `__tests__/unit/object-picker-menu.test.tsx` | 7 | `useDiagramStore` |
| `__tests__/unit/placement-preview.test.tsx` | 3 | `createRef` |

Delete the import specifier or the binding. Where the right-hand side is a call
with side effects, keep the call and drop only the binding. The ESLint config
ignores anything matching `^_`, so a binding that genuinely must stay can be
renamed instead.

### 3 × `@typescript-eslint/no-unused-expressions` — debris to delete

These are **not** pre-existing. The previous session's pruning script rewrote
`const x = <expression>;` into a bare `<expression>;` on lines whose right-hand
side had no side effects, leaving three dead statements:

| File | Line | Left behind |
| --- | --- | --- |
| `__tests__/properties/segment-drag-constraint.test.ts` | 96 | `[path[0], ...newWaypoints, path[path.length - 1]];` |
| `__tests__/properties/segment-drag-waypoints.test.ts` | 94 | `seg.index - 1;` |
| `__tests__/properties/viewport-transform.test.ts` | 13 | `1e-6;` |

Delete the statements outright. They compute nothing and are read by nothing.
Check the surrounding test still asserts what its name claims — if a test lost
its subject when the binding was pruned, restore the binding and use it rather
than deleting the line.

### 5 × `react-hooks/exhaustive-deps` — unstable dependencies

Real, if minor: a value built with `??` or `||` in the render body gets a new
identity every render, so every hook depending on it re-runs every render.

| File | Line | Value |
| --- | --- | --- |
| `src/components/canvas/objects/LineObjectComponent.tsx` | 107 | `labelOffset` |
| `src/components/config/schema/SchemaConfigForm.tsx` | 89 | `entries` (two hooks) |
| `src/components/config/schema/SchemaConfigForm.tsx` | 92 | `config` (two hooks) |

The fix ESLint suggests is right: wrap each in its own `useMemo` keyed on the
underlying value. `labelOffset` feeds the label drag handler, so this also
removes a needless handler re-creation on every canvas render.

### 2 × `@next/next/no-img-element` — decide, do not silence

| File | Line |
| --- | --- |
| `src/components/canvas/interactions/PlacementPreview.tsx` | 120 |
| `src/components/canvas/objects/ArchitectureBlockComponent.tsx` | 111 |

Both render AWS service icons from `AWS_ICON_REGISTRY`. `next/image` is built for
layout-managed page images, not for icons drawn inside an SVG canvas at a
viewport-derived scale, and it would add a loader between the registry path and
the element. The likely right answer is to keep `<img>` and disable the rule for
these two files with a comment explaining why — but confirm that the icons are
static local assets first, and if so consider disabling the rule for the canvas
directory in `eslint.config.mjs` rather than per line.

---

## Verification

From the repository root:

```
uv run pytest tests/ -n auto -q
uv run ruff check app/ tests/
```

From `frontend/` (the package manager is `corepack pnpm`; bare `pnpm` is not on
PATH, and these commands fail from the repository root):

```
corepack pnpm exec tsc --noEmit          # must stay at 0 errors
corepack pnpm eslint src __tests__       # 0 errors; warnings should reach 0
corepack pnpm vitest run
```

`next build` segfaults on host Node 22 but succeeds on the Node 24 used by
`build/Dockerfile.frontend`. To check the production build, use
`docker build -f build/Dockerfile.frontend --target builder .` instead of
building on the host.

New tests for Part 1 should be mutation-tested before being trusted: break the
behaviour deliberately, confirm the new test fails, then restore. Several tests
written against this area in earlier sessions passed regardless of the code under
test.
