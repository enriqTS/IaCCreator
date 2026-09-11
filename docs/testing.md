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

`tests/test_codebuild_secret_connections.py` covers native injection, external-role ownership, configuration validation, binding conflicts, and legacy registry defaults. Shared secret tests exercise deterministic aggregation, IAM/KMS scoping, preview ownership, and encrypted-project Terraform validation for Batch job definitions, Step Functions, MWAA, CodeBuild, and App Runner alongside Lambda, EC2, and ECS. `tests/test_app_runner_secret_connections.py` additionally verifies runtime/image-pull role separation, reserved environment names, public-image settings, and Terraform-evaluated merging of managed and external secret bindings.

`tests/test_launch_template_connections.py` covers managed template versions, duplicate/shared connections, conflicting templates, external template compatibility, catalog/schema exposure, and a complete VPC/subnet/security-group/route/Auto Scaling architecture validated by Terraform. `tests/test_placement_external_identifiers.py` derives cases from all list-placement registry entries and uses permutations to verify preservation of external IDs and deterministic repeated generation.

`tests/test_mwaa_secret_connections.py` verifies external execution-role ownership, missing-role rejection, empty read-access configuration, and absence of native injection or plaintext retrieval. MWAA also participates in shared secret aggregation, preview, KMS, and encrypted-project Terraform validation tests.

`tests/test_kms_access_integration.py` covers consumer-action KMS grants, shared service policies, external-key warnings, encryption flags, key conflicts, and mixed-service Terraform validation/plan graphs. `tests/test_iam_template_references.py` verifies that policy ARN placeholders evaluate to real values and foreign resources use module inputs.

`tests/test_step_functions_secret_connections.py` verifies executable SDK tasks, scoped external-role access, invalid placeholder/config rejection, sensitive-data warnings, and unchanged unconnected workflows. Terraform console tests evaluate task definitions and environment-override guards, preserving transitions, data paths, and unrelated workflow states.

`tests/test_batch_secret_connections.py` covers job/execution-role separation, native settings and reserved-name validation, external bindings, catalog/schema exposure, and unchanged compute-environment compatibility. Terraform console tests evaluate container properties, resource requirement types, plaintext-variable replacement, and managed/external secret merging. Shared tests cover aggregation and encrypted-project validation.

`conftest.py` provides Hypothesis strategies and shared helpers. New generator or serialization tests should extend those strategies where possible.

Any fixture that creates a `TestClient` from the real `app.main.app` must isolate persistence: monkeypatch `app.persistence.factory.get_repository`, reload `app.main`, and override `app.routers.diagrams.get_repo` through `app.dependency_overrides`. This prevents parallel workers from writing the real TinyDB file.

## Frontend

Frontend tests live in `frontend/__tests__/` and `frontend/src/utils/__tests__/`.

Property tests cover canvas-object creation/deletion/serialization, grouping, history, anchors, snapping, selection, placement, routing, line waypoints and segments, viewport transforms, sidebar search/pinning, and configuration visibility. Unit tests cover components, Zustand behavior, persistence/API clients, schema and connection panels, API Gateway editing, routing grid/pathfinder/router behavior, shortcuts, and tours.

Routing tests are split between the legacy deterministic routing helpers and the current `utils/routing/` grid/pathfinding implementation. Keep both suites when changing fallback behavior.

Use behavior-oriented tests rather than source-text assertions. For geometry and interaction changes, mutation-test the relevant rule when practical: deliberately break it, confirm the new test fails, then restore it.

`tests/test_s3_notification_connections.py` covers shared bucket notification ownership, external destinations, deterministic duplicates, converging SNS/SQS publishers, FIFO rejection, external-key warnings, shared KMS policies, filter conflicts, and preview ownership. A mixed architecture passes Terraform validation and plan-graph checks; registry-derived validation covers each new notification pair. Schema endpoint tests verify list-valued event defaults for all three destinations.

`tests/test_s3_eventbridge_connections.py` covers managed rule scoping, preserved filters, unsupported buses/schedules/patterns, duplicate and converging bucket connections, mixed direct notifications, preview ownership, and Terraform validation/plan graphs.

`tests/test_ebs_attachment_connections.py` covers volume-owned attachments, managed Availability Zone references, invalid/root device rejection, Linux device aliases, duplicate/multiple volume connections, unsupported Multi-Attach, preview guidance, and Terraform validation/plan graphs.

`tests/test_efs_lambda_connections.py` verifies access-point ownership, Lambda native mount blocks, filesystem-scoped permissions, network prerequisites, invalid bindings, shared filesystems, and generated-project Terraform validation. Existing EFS subnet and security-group placement supply its mount-target networking.

`tests/test_backup_selection_connections.py` covers all five resource types, exact ARN selection, role validation and conflicts, deterministic duplicates, preview ownership, and a mixed Terraform project. Shared fixtures now supply RDS/Aurora identifiers and Aurora's required engine for registry-derived validation.
