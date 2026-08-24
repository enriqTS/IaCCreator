# Implementation Plan: Overlay Configuration Panels

## Overview

Replace the lateral configuration sidebar with overlay panels, one per kind of
configurable thing — architecture objects, connections, and groups. The sidebar
is reduced to visual configuration only, and may be removed entirely if visual
editing moves to a floating toolbar.

Phases 1 and 2 are done, along with both carried-over items and the backend
contribution-preview endpoint they depend on. Phase 3 is decided but not built:
visual configuration moves to a floating toolbar. Phase 4 remains blocked.

---

## Motivation

The sidebar is a roughly 300px column that has to hold every field of whatever is
selected. Measured against the current schemas, the pressure comes from object
configuration rather than from connections:

| Surface | Field count |
| --- | --- |
| `api-gateway` block | 45 |
| `lambda` block | 37 |
| `s3` block | 34 |
| `dynamodb` block | 23 |
| median across the 49 services with a Terraform schema | 3 |
| richest connection (`api-gateway → lambda`, `route_handler`) | 4 |
| connections with no fields at all | 5 of 16 |

The distribution is heavily skewed: a handful of services are enormous and most
are trivial. Configuration complexity is expected to keep growing, particularly
once groups carry generation semantics.

---

## Current State

- `SidebarPanel.tsx` owns the whole surface. It derives a tab list per selected
  object (`getTabsForObject`) and renders `Variables`, `Connection` and `Visual`
  tabs.
- Connection configuration is reached indirectly: select the **line**, then open
  the `Connection` tab. `lineConnectorData` resolves the connector from the
  selected line.
- Field rendering is already schema-driven and generic:
  `SchemaConfigForm`, `SchemaFieldRenderer`, `MultiSelectFieldRenderer`,
  `LinkedSelectFieldRenderer`, `LinkedEntryFieldRenderer`.
- Schemas come from the backend: `/api/variable-schemas` for objects and
  `/api/connection-schemas` for connections.
- Groups exist only as frontend diagram state. `ObjectGroup` carries `id`, `name`
  and `memberIds`, is saved in `DiagramState`, and never reaches
  `serializeToArchitectureDescription`. `ArchitectureDescription` has no group
  field.

The generic field renderers and the schema endpoints are the reusable core. The
tab layout and the sidebar container are what goes away.

---

## Target State

A single overlay surface whose contents are chosen by the type of the thing being
configured. It is a centered modal over a dimmed canvas — the shape of a
browser's address-bar palette — so configuration is a focused mode entered and
left rather than a panel worked beside.

It opens on exactly three explicit gestures — placing the object or drawing the
connection, double-clicking it, and the configure item in its right-click context
menu. Selection alone never opens it. It closes on its X button, a click outside,
or Escape. Each type contributes a panel; the overlay itself is
a container and owns no per-type knowledge — the same universal-interface split
already used for connection handlers on the backend.

The overlay renders schema fields through the existing renderers, so adding a
field to a backend model continues to require no frontend change.

---

## Design Constraints

These came out of reviewing the current data and should hold for any design.

1. **Never open an empty overlay.** Five of sixteen connections have zero
   configurable fields. An empty panel covering the canvas is worse than an empty
   sidebar that was already being ignored.
2. **Never block — superseded.** The overlay is now a centered modal that dims
   the canvas, so it does gate it. What survives of this constraint is that
   nothing is ever forced: no connection has a single required field, all sixteen
   are fully defaulted, and the panel is always dismissible by its X, a click
   outside, or Escape.
3. **Keep the canvas visible where it matters.** Visual configuration (color,
   stroke, sizing) is edited while watching the result, which is exactly why it
   must not move into the modal. It goes to a floating toolbar instead (phase 3).
4. **Canvas signals matter more, not less.** An overlay is dismissed and gone,
   so the canvas becomes the only persistent indication of state — most
   importantly, that something is misconfigured.

---

## Delivered: the contribution preview

An overlay has room the sidebar does not. For connections with no fields, it can
show what the connection *will generate* — the IAM statements it contributes and
the Terraform resources it emits. That turns the five currently-empty panels into
the most informative surface in the application, and it fits the existing model
because the backend already computes exactly this in `ConnectionContribution`.

`POST /api/connections/preview` serves this. It runs the real handlers over the
built IR and returns, per connection, the Terraform resources emitted, the IAM
granted, and any issues — so the frontend infers nothing. It validates the same
way generation does, so a half-configured diagram returns 422 and the editor
shows no preview rather than a guess.

---

## Phases

### Phase 1 — Object configuration overlay — **done**

**Goal:** Move block configuration out of the sidebar. This is the largest
payoff, because it is where the crowding actually is (45, 37 and 34 fields).

`ConfigOverlay` is the container and `overlay-registry.tsx` is the per-type
dispatch; the container knows nothing about what it renders. Its target lives in
`configOverlayTargetId` on the store, set by the three opening gestures. A resolver returns
`null` when there is nothing to configure, so constraint 1 holds for objects too:
a service the backend serves no schema for opens no panel.

- Build the overlay container: explicitly opened, always dismissible, modal.
- Render object schemas through the existing `SchemaConfigForm`.
- Use the extra room for grouping — the schemas already carry a `group` on each
  `TerraformField`, which the sidebar cannot exploit well at its width.
- Leave the sidebar in place for the remaining tabs during this phase.

### Phase 2 — Connection configuration overlay — **done**

**Goal:** Move connection configuration to the same surface and stop routing it
through the line's tab list.

Selecting a line resolves its connector and opens the connection panel directly.
The contribution preview was built rather than suppressing empty panels, so all
sixteen connections open something worth reading; it is shown for every
connection, not only the five with no fields.

- Open the overlay from the connector itself rather than from the selected line.
- Apply constraint 1: connections with no fields either do not open a panel, or
  open the contribution preview described above.

### Phase 3 — Visual configuration split — **decided, not built**

**Goal:** Decide the fate of the sidebar.

- Visual configuration moves to a floating toolbar; `SidebarPanel` goes away with
  it. Judge the result by whether editing a color while watching the canvas still
  feels direct.
- The tab machinery is already gone: nothing depended on it once phases 1 and 2
  landed, so `SidebarPanel` now renders visual configuration directly. It still
  hosts the multi-selection summary and the global Terraform config, which both
  need a home before it can be removed.

### Phase 4 — Groups and group connections

**Blocked on backend design. Do not start from the UI.**

Group membership is intended to carry generation semantics, such as every
resource inside a VPC group being placed inside that VPC. That is a containment
model, not a panel: it changes which resources take VPC configuration, how subnet
and security-group wiring is produced, and how a connection crossing a group
boundary differs from one contained inside it.

Prerequisites, in order:

1. Design the server-side group model and add it to `ArchitectureDescription`.
2. Decide how groups affect generation, and how a group connection differs from a
   resource-to-resource connection.
3. Serialize groups from the frontend into the architecture payload.
4. Only then design the group panel, driven by the resulting schema.

Designing the panel first risks building a UI around a guess at the semantics and
rebuilding it afterwards.

---

## Carried over from the connection work

Two improvements were identified while completing the API Gateway to Lambda
connection and deliberately deferred. Both are now done:

- **Select a connection when it is created.** `PullToConnectOverlay` selects the
  line it just drew and opens its configuration.
- **Mark incomplete connections on the canvas.** `ConnectionIssueBadge` marks a
  line whose connection the backend reported an issue on. The judgement lives in
  the handler's `validate()` hook, so adding a new kind of incompleteness is a
  backend change with no frontend work.

A third idea — defaulting the sidebar to the `Connection` tab — was dropped on
purpose, because it is specific to the tab layout this plan removes.
