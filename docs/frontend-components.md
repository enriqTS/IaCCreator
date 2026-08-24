# Frontend Components

The Next.js frontend components in `frontend/src/components/` are organized into seven groups: canvas, config, menu, toast, toolbar, tour, and ui.

## Canvas (`frontend/src/components/canvas/`)

The core diagram rendering layer. Supports architecture blocks, geometric shapes, lines, text, and UML objects.

### `Canvas.tsx`

Main canvas container. Handles wheel events for zoom, middle-click/Space+left-click drag for pan, and left-click for object placement or deselection. Converts screen coordinates to canvas coordinates via `screenToCanvas()`.

### `CanvasBackground.tsx`

Renders the infinite dot grid background on an HTML5 Canvas element. The grid scales and translates with the viewport.

### `ElementLayer.tsx`

DOM overlay layer that renders interactive canvas object components positioned in canvas space. Handles object selection, dragging, marquee selection, and connector drawing.

### Object Components

| Component                          | Object Type          | Description                                    |
|------------------------------------|----------------------|------------------------------------------------|
| `ArchitectureBlockComponent.tsx`   | `architecture-block` | AWS service node with icon, name, config       |
| `ConnectionIssueBadge.tsx` | Marks a line whose connection the backend reported as incomplete; the message is shown as a native tooltip |
| `LineObjectComponent.tsx`          | `line`               | Line/arrow with optional anchoring to objects, orthogonal/diagonal routing |
| `GeometricObjectComponent.tsx`     | `geometric`          | SVG shapes (rectangle, ellipse, diamond, etc.) |
| `TextObjectComponent.tsx`          | `text`               | Editable text label on the canvas              |
| `UMLObjectComponent.tsx`           | `uml`                | UML diagrams (class, interface, actor, etc.)   |

### Canvas Interaction Components

| Component                    | Purpose                                                    |
|------------------------------|------------------------------------------------------------|
| `AlignmentGuides.tsx`        | Snap alignment guides shown during drag operations         |
| `AnchorIndicators.tsx`       | Circular anchor points shown on objects for line drawing. Single unified 20px circle per anchor (visual = interactive region) |
| `CanvasContextMenu.tsx`      | Right-click context menu on empty canvas                   |
| `CanvasObjectContextMenu.tsx`| Right-click context menu on selected objects               |
| `DragSizingOverlay.tsx`      | Resize handles overlay during drag-to-resize               |
| `GroupBoundingBox.tsx`       | Bounding box rendered around grouped objects               |
| `InlineRenameOverlay.tsx`    | Double-click-to-rename overlay for objects                 |
| `MarqueeSelection.tsx`       | Rectangular selection box for multi-select                 |
| `PlacementPreview.tsx`       | Ghost preview when placing a new object                    |
| `PullToConnectOverlay.tsx`   | Visual feedback when dragging to create a connection. Supports orthogonal preview routing |
| `ResizeHandles.tsx`          | Corner/edge resize handles for selected objects            |
| `SegmentHandles.tsx`         | Draggable handles on orthogonal line segments for manual waypoint adjustment |

## Config (`frontend/src/components/config/`)

All configuration lives in the overlay (`overlay/`). There is no sidebar: it was removed along with its width, collapse and side preferences, and the canvas is the only other surface.

### Config Overlay (`frontend/src/components/config/overlay/`)

| Component | Purpose |
|---|---|
| `ConfigOverlay.tsx` | The single configuration surface: a centered modal built on the shadcn `Dialog`, dimming the canvas behind it. Opens on placing an object, double-clicking one, or the context menu — never on selection alone. Closes on its X, a click outside, or Escape. Owns no per-type knowledge. |
| `ConfigTabs.tsx` | The shared tabbed layout every configuration panel uses. The strip scrolls horizontally when the tabs overflow, keeping tabs at their natural width so the next one stays partly visible as a hint; the scrollbar is hidden and edge arrows scroll it on click. |
| `overlay-registry.tsx` | Maps an object's type to the panel it contributes. Every canvas object gets one, because every object ends its tab strip with a Visual tab; objects with nothing else to configure open a visual-only panel. |
| `ConnectionOverlayPanel.tsx` | Connection fields under a Settings tab and the contribution preview under a Generated tab. A connection with no fields opens straight onto Generated. |
| `ConnectionContributionPreview.tsx` | Renders the backend's `ConnectionPreview`: reported issues, emitted Terraform resources, IAM granted. |

Adding a configurable kind of thing means adding a resolver to `overlay-registry.tsx`; the container does not change. Panels that own their own tabs (`SchemaConfigForm`, `ApigwDynamicConfigUI`, `ConnectionOverlayPanel`) take an `extraTabs` prop so the registry can append Visual without nesting a second tab strip. Every panel is laid out as tabs via `ConfigTabs` — this is the design pattern, so a new panel divides into tabs rather than into collapsible sections or one long form.

### `ConfigPanel.tsx`

Router component that renders the appropriate config form based on the selected element's `serviceType`.

### `SchemaConfigForm.tsx`

Schema-driven config form that dynamically renders fields based on `VARIABLE_SCHEMAS` fetched from the backend. Handles conditional visibility (`visible_when`), validation rules, grouped field layout, and option dropdowns. Replaces the individual per-service config forms with a single data-driven component.

### Visual Config Panels

| Component                    | Purpose                                                  |
|------------------------------|----------------------------------------------------------|
| `BlockVisualConfig.tsx`      | Width/height for architecture blocks                     |
| `LineVisualConfig.tsx`       | Color, width, stroke style, arrows for lines             |
| `GeoVisualConfig.tsx`        | Fill, border, dimensions for geometric shapes            |
| `TextVisualConfigPanel.tsx`  | Font size, color, alignment, bold/italic for text        |
| `UMLConfigPanel.tsx`         | Stereotype, attributes, methods for UML objects          |
| `VisualTab.tsx`              | Dispatches to the correct visual config panel            |

### Editors

| Component                        | Purpose                                              |
|----------------------------------|------------------------------------------------------|
| `KeyValueEditor.tsx`             | Generic key-value pair editor for `map` type variables (environment variables, tags) |
| `ListEditor.tsx`                 | Generic list editor for `list` type variables (Lambda layers) |

### API Gateway Config (`frontend/src/components/config/apigw/`)

Dedicated sub-components for the enhanced API Gateway configuration (routes, stages, authorizers, custom domains, VPC links).

### Other Config Components

| Component                        | Purpose                                              |
|----------------------------------|------------------------------------------------------|
| `GlobalTerraformConfigPanel.tsx` | Project-level Terraform settings (backend, provider) |
| `ZOrderControls.tsx`             | Bring to front/back, forward/backward buttons        |
| `PillIndicator.tsx`              | Small pill badge for tab indicators                  |
| `ResizeHandle.tsx`               | Drag handle for panel resizing                       |
| `panel-constants.ts`             | Min/max/default dimensions for panels                |

## Menu (`frontend/src/components/menu/`)

### `HamburgerMenu.tsx`

Top-level hamburger menu: new diagram, save/load, export to Terraform, project settings, preferences.

### `NewDiagramDialog.tsx`

Dialog for creating a new diagram. Resets the store state.

### `ProjectSettingsDialog.tsx`

Dialog for editing project name and environment configurations.

### `TerraformSettingsDialog.tsx`

Project-level Terraform configuration — backend, provider, version constraints, global variables — which belongs to no canvas object and so has no overlay panel. Reached from the hamburger menu; wraps `GlobalTerraformConfigPanel`.

### `PreferencesDialog.tsx`

Dialog for layout preferences: toolbar position (top/bottom), grid and snapping. Persisted via `useLayoutPreferencesStore`.

## Toast (`frontend/src/components/toast/`)

### `ToastProvider.tsx`

Renders toast notifications from `useToastStore`. Auto-dismiss after 4 seconds. Supports `success` and `error` types.

## Toolbar (`frontend/src/components/toolbar/`)

### `Toolbar.tsx`

Main toolbar with tool selection (pointer, connector) and action buttons (undo, redo, delete, export).

### `ObjectPickerMenu.tsx`

Unified object picker organized into categories: AWS Services (with search, abbreviation expansion, and recently-used tracking), Geometric Shapes (25+ shapes), and UML Diagrams (class, interface, actor, use-case, component, package, node). Selecting an item switches to the appropriate placement tool mode.

## Tour (`frontend/src/components/tour/`)

### `OnboardingTour.tsx`

Step-by-step onboarding tour highlighting key UI features for new users.

### `WelcomeDialog.tsx`

Welcome dialog shown on first visit with options to start the tour or dismiss.

## UI (`frontend/src/components/ui/`)

Shared shadcn/ui primitives: `button`, `card`, `checkbox`, `dialog`, `dropdown-menu`, `input`, `label`, `radio-group`, `select`, `sheet`, `tabs`, `tooltip`.
