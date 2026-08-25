# Canvas Test and Lint Work Record

This is a historical completion record, not current test or lint guidance.

The canvas interaction coverage originally planned here is implemented. Current tests include drag placement, tool-change resets, marquee selection, placement preview, drag sizing, routing, anchors, line segments, snapping, serialization, and canvas-object editing.

The old sidebar references are historical: configuration now uses the overlay, and `SidebarPanel.tsx` no longer exists.

For current commands and test-organization guidance, see [testing.md](testing.md). Use `uv run` for backend commands and `pnpm` from `frontend/` for frontend commands.
