# Frontend Components

The Next.js frontend components in `frontend/src/components/` are organized into six groups: canvas, config, menu, toast, toolbar, and ui.

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
| `LineObjectComponent.tsx`          | `line`               | Line/arrow with optional anchoring to objects  |
| `GeometricObjectComponent.tsx`     | `geometric`          | SVG shapes (rectangle, ellipse, diamond, etc.) |
| `TextObjectComponent.tsx`          | `text`               | Editable text label on the canvas              |
| `UMLObjectComponent.tsx`           | `uml`                | UML diagrams (class, interface, actor, etc.)   |
| `DiagramElement.tsx`               | (legacy)             | Legacy service node for backward compatibility |

### Canvas Interaction Components

| Component                    | Purpose                                                    |
|------------------------------|------------------------------------------------------------|
| `CanvasContextMenu.tsx`      | Right-click context menu on empty canvas                   |
| `CanvasObjectContextMenu.tsx`| Right-click context menu on selected objects               |
| `DragSizingOverlay.tsx`      | Resize handles overlay during drag-to-resize               |
| `InlineRenameOverlay.tsx`    | Double-click-to-rename overlay for objects                 |
| `MarqueeSelection.tsx`       | Rectangular selection box for multi-select                 |
| `PlacementPreview.tsx`       | Ghost preview when placing a new object                    |
| `PullToConnectOverlay.tsx`   | Visual feedback when dragging to create a connection       |
| `ResizeHandles.tsx`          | Corner/edge resize handles for selected objects            |
| `AnchorIndicators.tsx`       | Visual anchor points shown on objects during line drawing   |
| `GroupBoundingBox.tsx`       | Bounding box rendered around grouped objects               |

## Config (`frontend/src/components/config/`)

Configuration panels for selected objects. The primary UI uses a sidebar panel; a legacy bottom panel existed previously but has been removed from the codebase.

### `SidebarPanel.tsx`

Collapsible sidebar panel (left or right, configurable via preferences). Architecture blocks get "Variables" and "Visual" tabs; other objects get only "Visual". Supports drag-to-resize width. Exports `getTabsForObject()` utility for determining which tabs to show per object type. Includes `MultiSelectionView` and `SingleSelectionView` sub-components.

### `ConfigPanel.tsx`

Router component that renders the appropriate config form based on the selected element's `serviceType`.

### `SchemaConfigForm.tsx`

Schema-driven config form that dynamically renders fields based on `VARIABLE_SCHEMAS` fetched from the backend. Handles conditional visibility (`visible_when`), validation rules, grouped field layout, and option dropdowns. Replaces the individual per-service config forms (LambdaConfigForm, S3ConfigForm, etc.) with a single data-driven component.

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

### `PreferencesDialog.tsx`

Dialog for layout preferences: sidebar side (left/right) and toolbar position (top/bottom). Persisted via `useLayoutPreferencesStore`.

## Toast (`frontend/src/components/toast/`)

### `ToastProvider.tsx`

Renders toast notifications from `useToastStore`. Auto-dismiss after 4 seconds. Supports `success` and `error` types.

## Toolbar (`frontend/src/components/toolbar/`)

### `Toolbar.tsx`

Main toolbar with tool selection (pointer, connector) and action buttons (undo, redo, delete, export).

### `ObjectPickerMenu.tsx`

Unified object picker organized into categories: AWS Services (with search, abbreviation expansion, and recently-used tracking), Geometric Shapes (25+ shapes), and UML Diagrams (class, interface, actor, use-case, component, package, node). Selecting an item switches to the appropriate placement tool mode.

## UI (`frontend/src/components/ui/`)

Shared shadcn/ui primitives: `button`, `card`, `checkbox`, `dialog`, `dropdown-menu`, `input`, `label`, `radio-group`, `select`, `sheet`, `tabs`.
