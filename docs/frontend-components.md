# Frontend Components

The Next.js frontend components in `frontend/src/components/` are organized into five groups: canvas, config, menu, toast, and toolbar.

## Canvas (`frontend/src/components/canvas/`)

The core diagram rendering layer using a hybrid Canvas + DOM approach.

### `Canvas.tsx`

Main canvas container. Handles:
- Wheel events → zoom (via `useDiagramStore.zoom()`)
- Middle-click or Space+left-click drag → pan
- Left-click on empty canvas → deselect all or place a service (when in `place-service` tool mode)
- Converts screen coordinates to canvas coordinates via `screenToCanvas()`

Renders `CanvasBackground` and `ElementLayer` as children.

### `CanvasBackground.tsx`

Renders the infinite dot grid background on an HTML5 Canvas element. The grid scales and translates with the viewport.

### `ElementLayer.tsx`

DOM overlay layer that renders interactive `DiagramElement` components positioned in canvas space. Handles element selection, dragging, and connector drawing.

### `DiagramElement.tsx`

Individual service node rendered as a DOM element. Displays the service icon, name, and handles click/drag interactions. Positioned using CSS transforms based on canvas-to-screen coordinate conversion.

## Config (`frontend/src/components/config/`)

Service-specific configuration panels that appear when a diagram element is selected.

### `ConfigPanel.tsx`

Router component that renders the appropriate config form based on the selected element's `serviceType`. Dispatches to one of the service-specific forms below.

### Service Config Forms

Each form reads the selected element's config from the store and calls `updateElementConfig()` on change.

| Component                  | Service      | Fields                                                    |
|----------------------------|--------------|-----------------------------------------------------------|
| `LambdaConfigForm.tsx`     | Lambda       | handler, runtime, memory_size, timeout, is_layer          |
| `S3ConfigForm.tsx`         | S3           | versioning                                                |
| `DynamoDBConfigForm.tsx`   | DynamoDB     | billing_mode, hash_key, hash_key_type, range_key, range_key_type |
| `APIGatewayConfigForm.tsx` | API Gateway  | protocol_type                                             |
| `CloudWatchConfigForm.tsx` | CloudWatch   | retention_in_days                                         |
| `IAMConfigForm.tsx`        | IAM          | (minimal config)                                          |

## Menu (`frontend/src/components/menu/`)

Application-level menus and dialogs.

### `HamburgerMenu.tsx`

Top-level hamburger menu providing access to:
- New diagram
- Save/load diagrams (server and localStorage)
- Export to Terraform
- Project settings

### `NewDiagramDialog.tsx`

Dialog for creating a new diagram. Resets the store state.

### `ProjectSettingsDialog.tsx`

Dialog for editing project name and environment configurations (name + variables per environment).

## Toast (`frontend/src/components/toast/`)

### `ToastProvider.tsx`

Renders toast notifications from the `useToastStore`. Toasts auto-dismiss after 4 seconds. Supports `success` and `error` types.

## Toolbar (`frontend/src/components/toolbar/`)

### `Toolbar.tsx`

Main toolbar with tool selection (pointer, connector) and action buttons (undo, redo, delete, export).

### `AWSServicePicker.tsx`

Categorized service picker for placing AWS service nodes. Supports 200+ services across 26 categories. Selecting a service switches to `place-service` tool mode.
