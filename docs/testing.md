# Testing

## Commands

From the repository root:

```text
uv run pytest -n auto
uv run ruff check .
```

From `frontend/`:

```text
pnpm vitest run
pnpm lint
pnpm build
```

## Backend

Backend tests live in `tests/`. The suite combines generator/property tests, API tests, persistence tests, connection tests, and Terraform validation tests.

Key coverage areas include:

- typed service config, TerraformField metadata, schema serialization/validation, naming rules, and option enforcement;
- IR construction, stable resource identity, generator registration, variable wiring, execution-role ownership, and generated-project Terraform validation;
- API Gateway routes, authorizers, WebSocket routes, and backend OpenAPI import;
- every registered connection, connection schemas, aggregation, previews, EventBridge targets, S3 notifications, and DynamoDB streams;
- diagram CRUD, migrations, session isolation/middleware, and TinyDB/DynamoDB factory behavior.

`conftest.py` provides Hypothesis strategies and shared helpers. New generator or serialization tests should extend those strategies where possible.

Any fixture that creates a `TestClient` from the real `app.main.app` must isolate persistence: monkeypatch `app.persistence.factory.get_repository`, reload `app.main`, and override `app.routers.diagrams.get_repo` through `app.dependency_overrides`. This prevents parallel workers from writing the real TinyDB file.

## Frontend

Frontend tests live in `frontend/__tests__/` and `frontend/src/utils/__tests__/`.

Property tests cover canvas-object creation/deletion/serialization, grouping, history, anchors, snapping, selection, placement, routing, line waypoints and segments, viewport transforms, sidebar search/pinning, and configuration visibility. Unit tests cover components, Zustand behavior, persistence/API clients, schema and connection panels, API Gateway editing, routing grid/pathfinder/router behavior, shortcuts, and tours.

Routing tests are split between the legacy deterministic routing helpers and the current `utils/routing/` grid/pathfinding implementation. Keep both suites when changing fallback behavior.

Use behavior-oriented tests rather than source-text assertions. For geometry and interaction changes, mutation-test the relevant rule when practical: deliberately break it, confirm the new test fails, then restore it.
