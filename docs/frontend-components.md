# Frontend Components

Components under `frontend/src/components/` render the canvas editor and its supporting UI.

## Canvas

`canvas/Canvas.tsx` owns viewport and top-level interactions. `CanvasBackground.tsx` draws the grid, `ElementLayer.tsx` renders the DOM object layer, and `Minimap.tsx` provides diagram overview navigation.

Object renderers in `canvas/objects/` cover architecture blocks, semantic containers, lines, geometric shapes, text, UML, and connection issue badges. Semantic containers highlight valid and invalid drop targets during object movement. Dropping submits containment intent to the backend, while moving a container translates its full descendant subtree. Interaction components in `canvas/interactions/` cover selection, anchors, resize, line segment handles, placement, pull-to-connect, context menus, grouping, rename, alignment guides, and marquee selection.

Line routing uses `src/utils/routing/`; manual segment editing and routed previews are rendered through the line and interaction layers.

## Configuration

Configuration is centered in `config/overlay/`. `ConfigOverlay` is a modal container and `overlay-registry.tsx` selects the panel for the target object. It opens only through explicit placement, double-click, or context-menu actions.

`ConfigTabs` is the shared tab surface. Schema-backed service configuration is rendered by `schema/SchemaConfigForm.tsx` and field renderers; it consumes schemas served by the backend. Connection configuration uses `ConnectionOverlayPanel` and `ConnectionContributionPreview`, so generated resources, IAM grants, and issues come from the backend.

`config/apigw/` contains API Gateway-specific editing: routes (including WebSocket details), stages, authorizers, API keys, domains, expressions, detail panels, and OpenAPI import. `config/visual/` contains the Visual tab for every canvas-object type. Project-wide Terraform settings remain in `GlobalTerraformConfigPanel` and the menu dialog, rather than an object overlay.

## Navigation and supporting UI

- `objects/` is the permanent object sidebar: search, categories, pins, recent items, armed-placement state, and collapsed rail.
- `toolbar/Toolbar.tsx` contains drawing and editing tools.
- `menu/` contains diagram, project, Terraform, and preference dialogs.
- `shortcuts/KeyboardShortcutsOverlay.tsx` presents keyboard shortcut help.
- `toast/` and `tour/` provide notifications and onboarding.
- `ui/` contains shared shadcn/ui primitives.

The canvas is the product surface; configuration, menus, and dialogs should compose the existing shadcn primitives and remain secondary to it.
