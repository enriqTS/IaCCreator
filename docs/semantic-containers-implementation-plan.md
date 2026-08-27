# Semantic Containers Implementation Plan

## Purpose

This document defines the implementation plan for nested, backend-aware architecture containers. A semantic container is a visible canvas boundary whose membership can derive Terraform connections, deployment scope, and inherited configuration.

Initial examples include Region, Availability Zone, VPC, and Subnet boundaries. Placing an object inside one of these boundaries should automatically establish the relationships supported by the backend connection registry.

Semantic containers are distinct from the existing visual object groups. Visual groups remain an editing convenience with no infrastructure meaning.

## Goals

- Represent architecture scopes as visible, nestable canvas boundaries.
- Allow VPC and Subnet resource objects to render as containers without duplicating their Terraform identity.
- Derive registered service connections from containment.
- Inherit Region and Availability Zone scope where appropriate.
- Replace copied IDs and ARNs with Terraform references.
- Keep containment validation and transformation in the backend.
- Preserve visual grouping as an independent feature.
- Support persistence, undo/redo, preview, and generated Terraform validation.

## Non-goals

The initial implementation does not include:

- unrestricted multi-region Terraform generation;
- arbitrary parent-child relationships without Terraform or scope semantics;
- automatic creation of credentials or secret values;
- scaling child geometry when a container is resized;
- replacing explicit service connections that are not implied by containment;
- treating every visual overlap as infrastructure containment.

## Existing system

The editor already supports `ObjectGroup` records and an optional `groupId` on canvas objects. These groups:

- are flat and non-nestable;
- require at least two members;
- do not have independent dimensions or canvas rendering;
- select and move members together;
- have no backend or Terraform semantics;
- store membership in both `ObjectGroup.memberIds` and object `groupId` values.

The current diagram converter ignores groups when constructing `ArchitectureDescription`. Existing groups must remain unchanged and must not be extended to carry infrastructure semantics.

## Core design

### Separate visual and semantic grouping

Use independent concepts:

| Visual group | Semantic container |
|---|---|
| `ObjectGroup` | `SemanticContainer` or container-capable resource |
| Editing convenience | Architecture semantics |
| Flat | Nested |
| Temporary selection boundary | Persisted visible boundary |
| `groupId` | `parentContainerId` |
| No Terraform effect | Connections or inherited scope |

A canvas object may have both a visual `groupId` and a semantic `parentContainerId`.

### Resource containers

VPC and Subnet already represent Terraform resources. Do not create a second container object that secretly owns or duplicates the resource.

Add a presentation mode to resource objects:

```ts
presentation: 'node' | 'container';
parentContainerId?: string;
```

A VPC or Subnet in container presentation remains the same architecture resource with the same stable ID, configuration, outputs, and module. Only its canvas rendering and containment capability change.

### Scope containers

Region and Availability Zone are deployment scopes rather than standalone Terraform resources. Represent them as a dedicated canvas object:

```ts
interface SemanticContainerObject {
  id: string;
  objectType: 'semantic-container';
  containerType: string;
  name: string;
  position: Point;
  config: Record<string, unknown>;
  visualConfig: ContainerVisualConfig;
  parentContainerId?: string;
  zIndex: number;
  locked?: boolean;
}
```

Initial container types:

- `region`
- `availability-zone`
- `generic`

A generic container has no Terraform behavior unless the backend later assigns it typed semantics.

### Canonical hierarchy

`parentContainerId` is the canonical source of containment. Child collections are derived by indexing parent pointers and are not stored redundantly.

The hierarchy must support:

- one direct semantic parent per object;
- unlimited valid nesting depth;
- ancestor traversal;
- subtree movement;
- deterministic deletion and reparenting;
- cycle rejection.

## AWS semantic rules

Visual nesting must not be treated as a universal `contains` connection. AWS relationships differ by resource.

Initial rules include:

- a VPC is scoped to a Region;
- an Availability Zone belongs to a Region;
- a Subnet belongs to a VPC and one Availability Zone;
- a Security Group belongs to a VPC, not a Subnet;
- a workload can be placed in a Subnet;
- a workload uses Security Groups through separate associations;
- a NAT Gateway is placed in a Subnet;
- a Route Table belongs to a VPC and associates with Subnets.

If a Security Group is visually placed inside a Subnet, the backend should resolve the nearest VPC ancestor and derive VPC membership. It must not invent a Subnet → Security Group relationship.

A containment relationship can produce one of three outcomes:

1. **Terraform connection** — a registered `ConnectionSpec` produces module inputs, resources, or IAM grants.
2. **Inherited scope** — Region or Availability Zone values are inherited without a service connection.
3. **Visual-only containment** — the hierarchy is preserved but produces no Terraform contribution.

The backend must report which outcome applies.

## Backend-owned containment catalog

Expose typed containment capabilities through `/api/editor-bootstrap` or a dedicated typed endpoint.

The catalog must describe:

- available scope-container types;
- services that support container presentation;
- allowed direct parent types;
- allowed child types;
- ancestor types used for semantic resolution;
- derived connection type, when one exists;
- inherited fields and their precedence policy;
- whether a relationship is visual-only;
- lifecycle and placement restrictions.

The frontend uses this data only to render controls and eligible drop targets. It must not contain a duplicate compatibility table.

Suggested typed concepts:

```text
ContainerTypeDefinition
ServiceContainmentCapability
ContainmentRule
InheritedFieldRule
ContainmentCatalogResponse
```

A containment rule must not produce Terraform behavior unless the corresponding relationship is registered in `CONNECTION_SPECS`.

## Backend models

Extend canonical diagram state with:

- `SemanticContainerObject` in the discriminated canvas-object union;
- `parentContainerId` on containable objects;
- resource `presentation` mode;
- connector provenance for containment-managed connectors.

Extend serialized connectors with fields equivalent to:

```python
origin: Literal["explicit", "containment"] = "explicit"
container_id: str | None = None
```

The backend must validate:

- every parent reference exists;
- the parent is container-capable;
- the child is allowed in that parent;
- no object contains itself;
- the graph contains no cycle;
- Region and Availability Zone values are consistent;
- only one direct parent exists;
- managed and explicit connectors do not duplicate one another;
- retired or decorative services are not introduced through containment.

Increment the canonical diagram version and add a migration that leaves existing objects without a semantic parent and existing connectors with explicit provenance.

## Containment resolver

Add a focused backend service such as `ContainmentResolver`. Do not put hierarchy and inheritance logic directly in `DiagramConverter`, `IRBuilder`, or frontend Zustand slices.

The resolver should:

1. Build and validate the containment tree.
2. Traverse ancestors for each contained object.
3. Resolve effective Region and Availability Zone.
4. Resolve the nearest relevant VPC and Subnet ancestors.
5. Match semantic relationships to registered connection specifications.
6. Create, update, or remove managed connectors.
7. Resolve inherited configuration values.
8. Detect conflicts with explicit values and connectors.
9. Return typed issues and normalized state.

Suggested result shape:

```python
ContainmentResolution(
    effective_scopes=[...],
    derived_connections=[...],
    inherited_values=[...],
    issues=[...],
)
```

`DiagramConverter` should consume normalized containment output before constructing `ArchitectureDescription`.

## Managed connections

Containment-derived service relationships should use the existing connection pipeline:

```text
ContainmentResolver
  → managed connector
  → ConnectionSpec
  → ConnectionHandler
  → ConnectionContribution
  → FileTreeAssembler
```

Do not add a second Terraform-generation path for containers.

Managed connectors should be persisted because this provides:

- stable IDs;
- visible relationship state;
- connection preview support;
- standard IR generation;
- save/load consistency;
- deterministic removal and reparenting;
- easier debugging.

The frontend may render managed connectors differently or hide them based on a display preference, but they remain part of canonical state.

Users must not independently change a managed connector's endpoints. Removing one should either remove the corresponding containment relationship or be rejected with an explanation.

If an equivalent explicit connector already exists, normalization must adopt or preserve it and avoid creating a duplicate Terraform contribution.

## Containment operations API

Add a typed endpoint similar to the existing connection operation API:

```text
POST /api/diagrams/containment/apply
```

Supported operations should include:

- assign an object to a parent;
- remove an object from its parent;
- move a subtree;
- change Region or Availability Zone scope;
- switch a resource between node and container presentation.

A request should identify the object and intended parent by stable ID. The backend validates and returns canonical normalized diagram state.

The endpoint must return typed issues for:

- invalid parent type;
- containment cycle;
- conflicting Region/AZ scope;
- missing required connection support;
- configuration conflict;
- unsupported resource placement.

## Configuration inheritance

Use explicit precedence rules:

1. explicit resource override where the field permits overrides;
2. explicit connector configuration;
3. nearest semantic container;
4. ancestor container;
5. environment or global default.

Classify inherited fields by policy:

- `managed`: containment is authoritative;
- `overridable`: a child may explicitly override the inherited scope;
- `external-fallback`: a manual value is used only when no managed relationship exists.

Identity fields such as a managed `vpc_id` should normally be authoritative. A resource must not claim containment in one VPC while retaining a conflicting manually entered VPC ID.

The backend response should identify inherited fields and their source. Configuration panels render managed values as read-only and explain their origin.

When removing containment, restore only explicit external values that were preserved separately. Do not silently convert Terraform-derived values into copied literals.

## Region and Availability Zone behavior

### Initial implementation

The current project emits one global AWS provider Region. Initially:

- allow one effective deployment Region per environment;
- require Region containers to match the configured provider Region;
- use Region containers for visualization, inheritance, and validation;
- use Availability Zone containers to populate or validate AZ-aware resources;
- reject incompatible multi-region placement with a typed issue.

This initial limitation must be clear in the UI.

### Future multi-region project

True multi-region support requires a separate implementation covering:

- provider aliases;
- per-resource provider selection;
- Region-aware environment module calls;
- cross-region connection rules;
- regional outputs and references;
- global-service exceptions;
- environment-specific Region-container values.

Multi-region support must not block VPC, Subnet, and Availability Zone containment.

## Frontend state

Add a focused semantic-containment slice rather than extending `grouping-slice.ts`.

The slice should own only presentational interaction state and canonical state application:

- active drop target;
- candidate validity and issue display;
- pending containment operation;
- subtree selection helpers;
- application of backend-normalized state.

Backend-owned rules must remain in the bootstrap/catalog response.

Keep absolute canvas coordinates initially. Moving a container computes a delta and applies it to all descendants. Parent-relative coordinates would require invasive changes to routing, anchoring, selection, serialization, and hit testing without providing an initial benefit.

## Canvas rendering

Add a focused semantic container renderer with:

- title/header area;
- subtle border and background;
- configurable dimensions;
- nested padding;
- selection and resize handles;
- lower z-index than descendants;
- visual indication of container type and inherited scope;
- invalid-state badge support.

Container boundaries should not be treated as ordinary connector-routing obstacles. Otherwise connectors between children may route around the entire VPC or Subnet boundary.

Child rendering must not be clipped by default. Nested containers should remain independently selectable.

VPC and Subnet architecture blocks use this renderer in container presentation while preserving their resource-specific configuration overlay.

## Placement and reparenting

Geometry and hit testing remain frontend concerns.

During drag:

1. Find container bounds intersecting the dragged object.
2. Filter candidates using backend-provided containment capabilities.
3. Prefer the deepest valid candidate.
4. Highlight the candidate and expected semantic outcome.
5. Do not mutate canonical membership continuously.

On drop:

1. Submit the intended parent to the containment operation endpoint.
2. Apply the returned canonical state.
3. Display backend issues if placement is rejected.

Use either object-center containment or a configurable overlap threshold. An overlap threshold around 50% reduces accidental reparenting near a boundary.

Dragging an object out of its current container removes or changes its parent only after drop. The backend then removes obsolete managed connectors and inherited values.

## Moving and resizing containers

### Movement

Moving a container should move every descendant by the same canvas delta while preserving the hierarchy and child-relative arrangement.

Movement must update:

- object positions;
- nested container positions;
- anchored line geometry through existing anchor behavior;
- routing previews;
- undo/redo history.

### Resizing

Initial behavior:

- resizing does not scale children;
- resizing does not move children;
- the minimum size includes the title and optional descendant bounds;
- shrinking past descendants either stops at the minimum size or leaves children visually outside without changing membership until explicitly reparented.

Do not continuously change membership during resize.

## Deletion, copy, and history behavior

Define these behaviors explicitly:

- deleting a child removes its parent reference and derived connectors;
- deleting a container requires choosing cascade deletion or reparenting descendants;
- the initial default should reparent descendants to the deleted container's parent unless the user explicitly chooses cascade deletion;
- copying a complete subtree preserves internal parent references with new IDs;
- copying individual children clears parent references unless the parent is included;
- undo/redo snapshots include semantic hierarchy, presentation mode, and managed connectors;
- visual groups remain independent during all operations.

## Required connection dependencies

The first semantic-container milestone depends on these connections from `docs/service-connections-implementation-plan.md`:

- VPC → Subnet;
- VPC → Security Group;
- VPC → Route Table;
- VPC → Internet Gateway;
- VPC → Target Group;
- Subnet → NAT Gateway;
- Subnet → Route Table;
- Subnet → workload placement;
- Security Group → workload association.

Implement these connection specifications with semantic containers rather than hardcoding their Terraform behavior in the resolver.

## Phase 1 — Domain contracts

1. Define typed containment catalog response models.
2. Define container types and service containment capabilities.
3. Add `parentContainerId`, presentation mode, and connector provenance.
4. Add semantic container objects to frontend and backend unions.
5. Increment the diagram format version.
6. Add persistence migration and round-trip coverage.
7. Expose containment capabilities through the editor bootstrap or a dedicated endpoint.

### Completion criteria

- Existing diagrams migrate without visual or generation changes.
- The OpenAPI document fully describes containment payloads.
- Frontend types match backend contracts.
- Existing visual groups behave unchanged.

## Phase 2 — Validation and normalization

1. Implement containment tree construction.
2. Reject missing parents, invalid parents, self-parenting, and cycles.
3. Implement nearest-ancestor resolution.
4. Implement Region, AZ, VPC, and Subnet scope resolution.
5. Detect explicit-value and connector conflicts.
6. Add typed containment issues.
7. Integrate normalization into diagram normalize, save, load, preview, and generation flows.

### Completion criteria

- All API entry points observe the same containment invariants.
- Arbitrarily nested valid trees normalize deterministically.
- Invalid trees never reach generation.

## Phase 3 — Foundational connections

Implement the VPC, Subnet, Security Group, Route Table, gateway, and workload-placement connection specifications required by the initial containment rules.

### Completion criteria

- A contained networking architecture generates Terraform references rather than copied IDs.
- Multiple Subnet and Security Group memberships aggregate correctly.
- Every registered connection passes generated-project validation.

## Phase 4 — Managed connection derivation

1. Implement `ContainmentResolver`.
2. Derive managed connections only through registered specifications.
3. Add connector provenance and deterministic IDs.
4. Deduplicate explicit and derived relationships.
5. Remove obsolete connectors during reparenting.
6. Integrate derived connectors with preview and architecture conversion.
7. Add the containment operations endpoint.

### Completion criteria

- Reparenting updates generated Terraform relationships.
- Managed connectors survive save/load and rename operations.
- Explicit equivalent connectors never cause duplicate contributions.

## Phase 5 — Container rendering

1. Add the semantic container renderer.
2. Add Region and Availability Zone objects to the catalog.
3. Add VPC and Subnet container presentation.
4. Implement nested z-order and padding.
5. Add selection, resize, rename, lock, and context-menu behavior.
6. Exclude container backgrounds from routing obstacles.
7. Add minimap rendering.

### Completion criteria

- Nested boundaries remain usable at supported zoom levels.
- Child resources and connectors render above containers.
- VPC and Subnet retain their normal configuration overlays.

## Phase 6 — Drag, drop, and subtree movement

1. Add candidate-container hit testing.
2. Highlight valid and invalid targets.
3. Prefer the deepest eligible container.
4. Apply reparenting through the backend endpoint on drop.
5. Move descendants with parent containers.
6. Implement drag-out behavior.
7. Integrate with snapping, anchoring, routing, selection, and history.

### Completion criteria

- Objects can move into, between, and out of nested containers.
- Rejected placements leave canonical state unchanged.
- Undo/redo restores geometry and semantic relationships together.

## Phase 7 — Configuration experience

1. Display inherited fields and their source.
2. Make containment-managed fields read-only.
3. Show whether containment produces a connection, inherited scope, or visual-only membership.
4. Show derived connection previews.
5. Add “Move into,” “Remove from container,” and “Select container” actions.
6. Add node/container presentation switching for eligible resources.
7. Explain single-Region limitations.

### Completion criteria

- Users can understand why a field has a value and where it came from.
- No frontend transformation duplicates backend inheritance logic.

## Phase 8 — Extended service coverage

Expand containment rules as connection support grows:

- EFS mount targets in Subnets;
- Load Balancers in Subnets and VPCs;
- EKS, Lambda, Auto Scaling, MQ, MWAA, DMS, MemoryDB, and Network Firewall placement;
- Client VPN Subnet associations;
- Route 53 private-zone VPC associations;
- Backup and governance scopes where containment has concrete Terraform semantics.

Do not register visual-only product relationships as Terraform connections.

## Phase 9 — Advanced scope

Potential later work:

- collapsible containers;
- automatic container layout;
- generic typed architecture boundaries;
- environment-specific scope views;
- provider alias and multi-region generation;
- cross-region connection validation;
- import of existing architectures into semantic boundaries.

## Backend tests

Add coverage for:

- valid and invalid containment trees;
- cycle rejection;
- invalid parent-child combinations;
- nearest-ancestor resolution;
- Security Group resolution through a Subnet to its VPC;
- Region/AZ/Subnet consistency;
- inherited-value precedence;
- managed connector creation and removal;
- explicit connector deduplication;
- reparenting;
- child and container deletion;
- diagram migration and persistence round trips;
- architecture conversion;
- connection preview;
- Terraform validation of containment-derived relationships.

Use property-based tests for arbitrary valid trees and sequences of assign, reparent, remove, and delete operations.

## Frontend tests

Add coverage for:

- nested container rendering;
- deepest-container hit testing;
- valid and invalid target highlighting;
- dragging into, between, and out of containers;
- moving a container with descendants;
- resizing without scaling children;
- independent visual and semantic grouping;
- selection and context-menu behavior;
- copy and paste of complete and partial subtrees;
- undo/redo;
- serialization round trips;
- minimap behavior;
- routing around resources without treating container backgrounds as obstacles;
- connector stability after subtree movement.

Use fast-check for containment trees, geometry operations, and state-operation sequences where practical.

## Risks and mitigations

### Visual containment may imply incorrect AWS semantics

Use backend-owned parent-child and ancestor-resolution rules. Never derive a generic `contains` Terraform relationship.

### Duplicate explicit and managed connections

Persist connector provenance and normalize equivalent relationships to one contribution.

### Hierarchy corruption

Use one canonical parent pointer, backend cycle validation, and property-based state-operation tests.

### Accidental reparenting

Use overlap thresholds, target highlighting, and finalization only on drop.

### Configuration conflicts

Classify fields as managed, overridable, or external fallback and return typed conflict issues.

### Routing degradation

Exclude semantic boundaries from ordinary obstacle collection and route around actual resources.

### Multi-region expectations

Initially enforce one effective provider Region per environment and treat true multi-region support as a separate project.

### Resource identity duplication

Render VPC and Subnet resources as containers rather than creating wrapper resources with hidden Terraform ownership.

## Recommended initial milestone

Deliver one vertical slice:

1. VPC resource container presentation.
2. Subnet resource container presentation.
3. Region and Availability Zone scope containers.
4. `parentContainerId` persistence and migration.
5. Backend containment validation and normalization.
6. VPC → Subnet managed connection.
7. VPC → Security Group ancestor-derived connection.
8. Subnet Availability Zone inheritance.
9. Drag/drop reparenting and subtree movement.
10. Inherited-field display and connection preview.
11. Generated-project Terraform validation.

This milestone proves the complete architecture without requiring all service-placement relationships at once.

## Definition of completion

The semantic-container system is complete when:

- visual groups and semantic containers remain independent;
- VPC and Subnet resources can render as nested boundaries without duplicate identities;
- Region and Availability Zone scope is backend validated;
- containment hierarchies persist and migrate safely;
- the backend is the source of truth for allowed placement and inherited behavior;
- containment-derived Terraform behavior uses registered connection handlers;
- managed and explicit connections do not duplicate contributions;
- moving and reparenting objects updates geometry and infrastructure semantics together;
- inherited configuration is visible and attributable in the editor;
- generated projects use Terraform references instead of copied managed-resource identifiers;
- backend and frontend property tests cover arbitrary hierarchy operations;
- generated projects pass applicable Terraform validation.
