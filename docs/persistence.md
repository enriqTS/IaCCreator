# Persistence Layer

`app/persistence/` provides a repository abstraction for anonymous-session users and saved diagrams.

## Interface

`AbstractRepository` defines:

| Area | Methods |
|---|---|
| Users | `create_user`, `get_user`, `update_user_last_active` |
| Diagrams | `save_diagram`, `get_diagram`, `list_diagrams`, `update_diagram`, `delete_diagram` |

`UserRecord`, `DiagramRecord`, and `DiagramSummary` are defined in `app/persistence/models.py`.

## Backends

`TinyDBRepository` is the default local backend. It stores `users` and `diagrams` tables in `data/db.json` and extracts `projectName` for the diagram summary.

`DynamoDBRepository` uses a `Users` table keyed by `session_id` and a `Diagrams` table keyed by `diagram_id`, with `session_id-index` for session-scoped listing. It supports custom table names, index name, endpoint URL, and region in its constructor.

`get_repository()` selects `tinydb` or `dynamodb` from `PERSISTENCE_BACKEND`, defaulting to TinyDB. The factory intentionally performs backend imports lazily.

## Router and migration behavior

The diagram router obtains its repository through the `get_repo` FastAPI dependency. This makes it independently overridable in integration tests; it is not initialized by a router-level `set_repository()` call.

Diagram state is stored as the submitted serialized payload. On reads, the diagram service migrates older persisted versions before the state is returned. The frontend serialization types and the backend validator/migrations must change together whenever the persisted format changes.
