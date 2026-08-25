# Overlay Configuration Work Record

This document records the completed migration from the configuration sidebar to the configuration overlay.

## Delivered

- `ConfigOverlay` is the single modal configuration surface.
- `overlay-registry.tsx` maps canvas-object types to their panels; the container has no per-type branching.
- The overlay opens only through placement, double-click, or a context-menu action, never selection alone.
- Schema-backed architecture-block fields use the backend-served variable schemas.
- Connection settings and backend-generated contribution previews share `ConnectionOverlayPanel`.
- Every canvas-object kind has a Visual tab.
- The former configuration sidebar was deleted; the permanent left sidebar is the object picker.
- Global Terraform settings remain in the hamburger-menu dialog because they do not belong to a canvas object.

The API Gateway editor has its own overlay detail flow and supports backend OpenAPI import.

## Remaining design boundary: groups

Groups remain frontend diagram state. They have no generation semantics and are not part of `ArchitectureDescription`. Any future group configuration must begin with backend containment and generation design, then add a typed API model and serialization, before creating UI panels.

Connection kinds, editable fields, defaults, generated resources, IAM grants, and warnings remain backend-defined through the connection registry and its schema/preview endpoints.
