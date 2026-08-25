# Database

The persistence layer supports TinyDB for local development and DynamoDB for production. Both store anonymous-session users and diagrams through the same repository interface.

## TinyDB

`TinyDBRepository` stores `users` and `diagrams` tables in `data/db.json` by default. It creates the parent directory as needed and uses UUID v4 IDs for diagrams.

A user record contains `session_id`, `created_at`, and `last_active`. A diagram record contains `diagram_id`, `session_id`, `project_name`, `diagram_state`, `created_at`, and `updated_at`.

## DynamoDB

`DynamoDBRepository` uses:

- `Users`, partitioned by `session_id`.
- `Diagrams`, partitioned by `diagram_id`, with the `session_id-index` GSI for session-scoped listing.

The constructor accepts table names, index name, endpoint URL, and region. Updates and deletes use conditional expressions so a missing diagram returns `False`.

## Persisted diagram state

`diagram_state` is the validated frontend serialization, not an independent database schema. The current client format is defined by `frontend/src/types/serialization.ts` and is canvas-object based. It includes project and environment data, serialized canvas objects, connectors, viewport, optional object groups, global Terraform configuration, and optional global routing mode.

Architecture blocks carry service config and Terraform variables. Lines may carry endpoints, anchor object IDs and positions, and manual waypoints. Connectors carry `sourceId`, `targetId`, `connectionType`, and optional `connection_config`.

Persisted diagram versions are upgraded by `app/services/diagram_migrations.py` when loaded. Do not add a second example schema here without updating the frontend serialization types, backend `DiagramStateInput`, and migrations together.
