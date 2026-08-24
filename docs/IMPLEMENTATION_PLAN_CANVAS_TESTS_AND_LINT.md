# Implementation Plan: Canvas Interaction Tests and Remaining Lint

## Overview

Two independent items left over after the hook-rules refactor:

1. **Canvas interaction behaviour has no test coverage**, including code that
   refactor changed. This is the one with real risk.
2. **7 ESLint warnings** remain, all needing a judgement call rather than a
   deletion. The 11 mechanical ones have since been cleared.

Neither blocks anything. Item 1 should be done first, because it protects work
already shipped.

**Both items are now done.** Final state: 0 TypeScript errors, 0 ESLint errors,
0 ESLint warnings, 806 backend tests and 1323 frontend tests passing, and the
production frontend image builds.

This is a record of finished work, so it still names `SidebarPanel.tsx` and its
tab test ids. The sidebar has since been deleted and all configuration moved into
the overlay — see `IMPLEMENTATION_PLAN_OVERLAY_CONFIG.md`.

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
| `MarqueeSelection` | `__tests__/unit/marquee-selection.test.tsx` | rect geometry, highlights, selection, thresholds |
| `Canvas` drag placement | `__tests__/unit/canvas-drag-placement.test.tsx` | preview, endpoints, snapping, viewport |
| Tool-change resets | `__tests__/unit/canvas-tool-change-reset.test.tsx` | every reset, and resuming after abandonment |

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

### Phase 1 — Drag placement — done

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

### Phase 2 — Tool-change resets — done

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

### Phase 3 — Sidebar tab reset — done

**Goal:** cover the one non-canvas component that took the same change.

- Selecting a different object returns the sidebar to its first tab.
- Selecting an object whose tab set does not include the active tab falls back to
  the first available tab.

### Phase 4 — Marquee selection — done

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

## Part 2: The Remaining 7 Warnings — done

`corepack pnpm eslint src __tests__` from `frontend/` now reports nothing.

### Done — 11 mechanical warnings cleared

The 8 dead test bindings and the 3 bare-expression statements have been removed.
Deleting one of those statements exposed that
`__tests__/properties/segment-drag-constraint.test.ts` was tautological: it built
its expected path by hand and asserted the values it had just written, never
reading `computeNewWaypoints`'s output. It now asserts the property its name
claims — that dragging along one axis introduces no new coordinate on the other —
and was mutation-tested against a deliberately broken `computeNewWaypoints`.

### 5 × `react-hooks/exhaustive-deps` — unstable dependencies

Real, if minor: a value built with `??` or `||` in the render body gets a new
identity every render, so every hook depending on it re-runs every render.

| File | Line | Value |
| --- | --- | --- |
| `src/components/canvas/objects/LineObjectComponent.tsx` | 107 | `labelOffset` |
| `src/components/config/schema/SchemaConfigForm.tsx` | 89 | `entries` (two hooks) |
| `src/components/config/schema/SchemaConfigForm.tsx` | 92 | `config` (two hooks) |

Fixed as ESLint suggested: each is wrapped in its own `useMemo` keyed on the
underlying value. `labelOffset` feeds the label drag handler, so this also
removed a needless handler re-creation on every canvas render. `entries` is keyed
on `schemas` and `serviceType`, which is sound because `getSchemas()` returns a
stable module-level object rather than a fresh one per call.

### 2 × `@next/next/no-img-element` — decide, do not silence

| File | Line |
| --- | --- |
| `src/components/canvas/interactions/PlacementPreview.tsx` | 120 |
| `src/components/canvas/objects/ArchitectureBlockComponent.tsx` | 111 |

Both render AWS service icons from `AWS_ICON_REGISTRY`. `next/image` is built for
layout-managed page images, not for icons drawn inside an SVG canvas at a
viewport-derived scale, and it would add a loader between the registry path and
the element.

All 317 registry entries were confirmed to be local static SVGs under
`public/aws-icons/`, with no remote or `data:` URIs, so `<img>` is kept. The rule
is disabled per line rather than for the canvas directory, because
`ObjectPickerMenu.tsx` already silences it that way for an icon from the same
registry, and a directory-wide override would also hide genuinely new offenders.

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

Every reset and geometry rule these tests cover was mutation-tested that way.
Three mutations initially survived and each pointed at a real gap:

- Dropping `PlacementPreview`'s pointer-position reset changed nothing, because
  the render guard hid the stale ghost anyway. The test now returns to
  `place-service` and asserts the ghost stays away until the pointer moves again.
- Dropping `SidebarPanel`'s `effectiveTab` fallback changed nothing, because the
  selection-change reset already picks a valid tab. The fallback is only reachable
  when the panel mounts with a selection already in place, which is what the test
  now exercises.
- Removing the marquee's 2px click threshold changed nothing while the gesture
  ended over empty canvas. The test now presses over an object, so a lost
  threshold would wrongly select it.

Two mutations that survive are not gaps. `DragSizingOverlay` and
`MarqueeSelection` each guard the same behaviour twice — an effect early-return
and a render guard — so removing either alone is invisible; removing both does
fail the tests.
