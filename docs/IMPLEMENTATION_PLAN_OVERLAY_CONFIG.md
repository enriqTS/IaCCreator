# Implementation Plan: Overlay Configuration Panels

## Overview

Replace the lateral configuration sidebar with overlay panels, one per kind of
configurable thing — architecture objects, connections, and groups. The sidebar
is reduced to visual configuration only, and may be removed entirely if visual
editing moves to a floating toolbar.

This is planned work to be started **after** the connection system is finished.
Nothing here is in progress.

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

A single overlay surface, opened by selection, whose contents are chosen by the
type of the selected thing. Each type contributes a panel; the overlay itself is
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
2. **Never block.** No connection has a single required field — all sixteen are
   fully defaulted. There is nothing to force the user to answer, so the overlay
   must be dismissible and must not gate the canvas.
3. **Keep the canvas visible where it matters.** Visual configuration (color,
   stroke, sizing) is edited while watching the result. That argues against
   putting visual config in an overlay that covers the canvas, and in favour of
   keeping a thin sidebar or moving it to a floating toolbar.
4. **Canvas signals matter more, not less.** An overlay is dismissed and gone,
   so the canvas becomes the only persistent indication of state — most
   importantly, that something is misconfigured.

---

## Opportunity: make empty panels informative

An overlay has room the sidebar does not. For connections with no fields, it can
show what the connection *will generate* — the IAM statements it contributes and
the Terraform resources it emits. That turns the five currently-empty panels into
the most informative surface in the application, and it fits the existing model
because the backend already computes exactly this in `ConnectionContribution`.

This would need a backend endpoint that previews a connection's contribution
rather than the frontend inferring it.

---

## Phases

### Phase 1 — Object configuration overlay

**Goal:** Move block configuration out of the sidebar. This is the largest
payoff, because it is where the crowding actually is (45, 37 and 34 fields).

- Build the overlay container: opened by selection, dismissible, non-blocking.
- Render object schemas through the existing `SchemaConfigForm`.
- Use the extra room for grouping — the schemas already carry a `group` on each
  `TerraformField`, which the sidebar cannot exploit well at its width.
- Leave the sidebar in place for the remaining tabs during this phase.

### Phase 2 — Connection configuration overlay

**Goal:** Move connection configuration to the same surface and stop routing it
through the line's tab list.

- Open the overlay from the connector itself rather than from the selected line.
- Apply constraint 1: connections with no fields either do not open a panel, or
  open the contribution preview described above.

### Phase 3 — Visual configuration split

**Goal:** Decide the fate of the sidebar.

- Move visual configuration to a floating toolbar, or keep a thin visual-only
  sidebar.
- Judge by whether editing a color while watching the canvas still feels direct.
- Remove `SidebarPanel`'s tab machinery once nothing else depends on it.

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
connection and deliberately deferred. Both survive this migration and should be
picked up with it rather than against the sidebar:

- **Select a connection when it is created.** `PullToConnectOverlay` currently
  calls `addConnector` and selects nothing, so drawing a connection produces no
  visible response. This is store behaviour and is independent of the surface.
- **Mark incomplete connections on the canvas.** An `api-gateway → lambda`
  connection with no matching route generates an integration and an invoke
  permission but no route at all, which is valid Terraform that deploys and can
  never invoke the function. Under an overlay this matters more, per constraint 4.
  The judgement of "incomplete" belongs in the backend, since the frontend is a
  renderer.

A third idea — defaulting the sidebar to the `Connection` tab — was dropped on
purpose, because it is specific to the tab layout this plan removes.
