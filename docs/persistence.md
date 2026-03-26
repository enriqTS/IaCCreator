# Persistence Layer

The `app/persistence/` package implements a repository pattern with swappable storage backends for user sessions and diagrams.

## Abstract Interface (`app/persistence/base.py`)

`AbstractRepository` is an ABC defining the persistence contract. All backends must implement:

### User Operations

| Method                          | Description                                      |
|---------------------------------|--------------------------------------------------|
| `create_user(session_id)`       | Create a new user record, returns `UserRecord`   |
| `get_user(session_id)`          | Look up user by session ID, returns `UserRecord` or `None` |
| `update_user_last_active(session_id)` | Update the `last_active` timestamp          |

### Diagram Operations

| Method                          | Description                                      |
|---------------------------------|--------------------------------------------------|
| `save_diagram(session_id, diagram)` | Save a new diagram, returns the assigned `diagram_id` |
| `get_diagram(diagram_id)`       | Load a diagram by ID, returns `DiagramRecord` or `None` |
| `list_diagrams(session_id)`     | List `DiagramSummary` entries for a session      |
| `update_diagram(diagram_id, diagram)` | Update an existing diagram, returns `bool`  |
| `delete_diagram(diagram_id)`    | Delete a diagram by ID, returns `bool`           |

## Data Models (`app/persistence/models.py`)

### `UserRecord`

- `session_id: str`
- `created_at: str` (ISO 8601)
- `last_active: str` (ISO 8601)

### `DiagramRecord`

- `diagram_id: str`
- `session_id: str`
- `project_name: str`
- `diagram_state: dict`
- `created_at: str` (ISO 8601)
- `updated_at: str` (ISO 8601)

### `DiagramSummary`

- `diagram_id: str`
- `project_name: str`
- `updated_at: str` (ISO 8601)

## TinyDB Backend (`app/persistence/tinydb_repo.py`)

`TinyDBRepository` stores data in a single JSON file (default `data/db.json`) with two TinyDB tables: `users` and `diagrams`.

- Creates the data directory automatically on init
- Generates UUID v4 diagram IDs
- Uses `tinydb.where()` for queries
- Extracts `projectName` from the diagram dict for the `project_name` field

Suitable for local development. No external dependencies beyond the `tinydb` package.

## DynamoDB Backend (`app/persistence/dynamodb_repo.py`)

`DynamoDBRepository` uses two DynamoDB tables:

- `Users` table — partition key: `session_id`
- `Diagrams` table — partition key: `diagram_id`, GSI `session_id-index` on `session_id`

Constructor parameters:
- `users_table_name` (default `"Users"`)
- `diagrams_table_name` (default `"Diagrams"`)
- `session_index_name` (default `"session_id-index"`)
- `endpoint_url` (optional, for local DynamoDB)
- `region_name` (optional)

Uses `boto3.resource("dynamodb")` and supports conditional expressions for updates and deletes.

## Factory (`app/persistence/factory.py`)

`get_repository()` reads the `PERSISTENCE_BACKEND` environment variable:

| Value       | Backend              |
|-------------|----------------------|
| `tinydb`    | `TinyDBRepository`   |
| `dynamodb`  | `DynamoDBRepository` |

Default is `tinydb`. Raises `ValueError` for unknown values. Imports are lazy to avoid loading boto3 when using TinyDB.
