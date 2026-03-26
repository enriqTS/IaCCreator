# Database

The data layer supports two storage backends: TinyDB for local development and DynamoDB for production.

## TinyDB (Local Development)

### File Location

`data/db.json` — a single JSON file created automatically on first use.

### Tables

The TinyDB instance contains two tables:

**`users` table:**
```json
{
  "session_id": "uuid-v4",
  "created_at": "2025-01-01T00:00:00+00:00",
  "last_active": "2025-01-01T12:00:00+00:00"
}
```

**`diagrams` table:**
```json
{
  "diagram_id": "uuid-v4",
  "session_id": "uuid-v4",
  "project_name": "my-project",
  "diagram_state": { ... },
  "created_at": "2025-01-01T00:00:00+00:00",
  "updated_at": "2025-01-01T12:00:00+00:00"
}
```

The `diagram_state` field stores the full frontend diagram state (version, elements, connectors, viewport, environments).

### Querying

TinyDB uses `tinydb.where()` for lookups:
- Users are queried by `session_id`
- Diagrams are queried by `diagram_id` or filtered by `session_id`

## DynamoDB (Production)

### Table Schema

**`Users` table:**
- Partition key: `session_id` (String)
- Attributes: `created_at`, `last_active` (ISO 8601 strings)

**`Diagrams` table:**
- Partition key: `diagram_id` (String)
- GSI `session_id-index`: partition key `session_id` (String)
- Attributes: `session_id`, `project_name`, `diagram_state` (Map), `created_at`, `updated_at`

### Configuration

The `DynamoDBRepository` constructor accepts:
- `users_table_name` (default `"Users"`)
- `diagrams_table_name` (default `"Diagrams"`)
- `session_index_name` (default `"session_id-index"`)
- `endpoint_url` (for local DynamoDB, e.g., `http://localhost:8000`)
- `region_name`

### Operations

- Diagram listing uses the `session_id-index` GSI with `Key("session_id").eq()`
- Updates use `ConditionExpression="attribute_exists(diagram_id)"` to ensure the item exists
- Deletes use the same condition expression, returning `False` on `ConditionalCheckFailedException`

## Data Schema: `diagram_state`

The `diagram_state` dict stored in both backends follows this shape:

```json
{
  "version": 1,
  "projectName": "my-project",
  "environments": [
    {"name": "dev", "variables": {"region": "us-east-1"}}
  ],
  "elements": [
    {
      "id": "uuid",
      "type": "lambda",
      "x": 100.0,
      "y": 200.0,
      "name": "my-function"
    }
  ],
  "connectors": [
    {
      "id": "uuid",
      "sourceId": "element-uuid",
      "targetId": "element-uuid",
      "type": "triggers"
    }
  ],
  "viewport": {"x": 0.0, "y": 0.0, "zoom": 1.0}
}
```
