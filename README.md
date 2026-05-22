# IaCCreator

A visual AWS architecture diagram editor with Terraform IaC generation.

Design your cloud architecture by placing AWS service nodes on an infinite canvas, connecting them, configuring service-specific properties, and exporting the result as a production-ready Terraform project — all from the browser.

The project consists of two integrated parts:
- **Frontend** — Next.js 16 visual diagram editor with pan/zoom canvas, drag-and-drop service placement, and real-time configuration
- **Backend** — FastAPI service that transforms architecture descriptions into modular Terraform file structures, with anonymous session management and diagram persistence

The frontend and backend communicate via a RESTful API with cookie-based anonymous sessions. Diagrams are persisted server-side using TinyDB (local development) or DynamoDB (AWS production). No login is required — users are identified by a session cookie that lasts 30 days.

## Supported AWS Services

Full Terraform generation (with service-specific config panels and HCL output):

**Core:**
- Lambda (including Lambda Layers)
- S3
- API Gateway (v2)
- DynamoDB
- IAM
- CloudWatch
- SNS
- SQS

**Compute:**
- EC2
- ECS
- EKS
- Elastic Beanstalk
- App Runner
- Batch
- EC2 Image Builder
- Lightsail
- ECR

**Analytics:**
- Athena
- CloudSearch
- EMR
- Glue
- Kinesis
- Kinesis Firehose
- MSK
- OpenSearch
- Redshift

**Database:**
- Aurora
- DocumentDB
- ElastiCache
- Neptune
- RDS
- Timestream

**Developer Tools:**
- CodeBuild
- CodeCommit
- CodeDeploy
- CodePipeline

**Business Applications:**
- Connect
- SES
- Pinpoint

**Other:**
- AppStream
- Amplify
- GameLift

Additionally, 270+ AWS services are available as icon-only diagram nodes (no Terraform generation) for visual architecture documentation.

## Generated Output Structure

```
my-project/
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── terraform.tfvars
│   └── prod/
│       └── ...
├── modules/
│   ├── lambda/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── my-function/
│   │       ├── lambda.tf
│   │       ├── iam.tf
│   │       ├── variables.tf
│   │       └── outputs.tf
│   ├── s3/
│   │   └── my-bucket/
│   │       ├── s3.tf
│   │       ├── variables.tf
│   │       └── outputs.tf
│   ├── dynamodb/
│   │   └── ...
│   ├── api-gateway/
│   │   └── ...
│   ├── cloudwatch/
│   │   └── ...
│   └── <service-type>/
│       └── ...
└── iam-policies/
    └── my-function-policy.json
```

## Getting Started

### Prerequisites

- Docker and Docker Compose

### Running with Docker (recommended)

```bash
docker compose up --build
```

This starts both the frontend and backend. Open `http://localhost:3000` in your browser.

To run in the background:

```bash
docker compose up --build -d
```

To stop:

```bash
docker compose down
```

Diagram data is persisted in a Docker volume, so it survives container restarts.

### Pulling the latest version (testers)

If you received the `docker-compose.testers.yml` file:

```bash
docker compose -f docker-compose.testers.yml pull
docker compose -f docker-compose.testers.yml up
```

This pulls pre-built images from the container registry — no source code or build step needed.

### Running without Docker (manual setup)

<details>
<summary>Click to expand</summary>

#### Prerequisites

- Python 3.14+
- Node.js 24+

#### Backend

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

By default, the backend uses TinyDB for local persistence (stored in `data/db.json`). To use DynamoDB instead, set:

```bash
PERSISTENCE_BACKEND=dynamodb
```

To configure the allowed frontend origin for CORS:

```bash
CORS_ORIGIN=http://localhost:3000  # default
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

The diagram editor will be available at `http://localhost:3000`.

To point the frontend at a different backend URL:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000  # default
```

Next.js rewrites automatically proxy `/api/*` and `/generate/*` requests to the backend.

</details>

### Run Tests

```bash
# Backend
pytest

# Frontend
cd frontend
npx vitest run
```

## Frontend

The diagram editor is a Next.js 16 (App Router) + Tailwind CSS single-page application using a hybrid Canvas + DOM rendering approach.

### Tech Stack

- Next.js 16 with React 19 and TypeScript
- Zustand for state management
- HTML5 Canvas for grid/connectors, DOM overlay for interactive service nodes and canvas objects
- Vitest + fast-check for unit and property-based testing

### Features

- Infinite pan/zoom canvas with dot grid background
- Place AWS service nodes from a categorized picker with search (310+ services, 26 categories) and recently-used tracking
- Place geometric shapes (26 types: rectangle, ellipse, diamond, hexagon, cylinder, cloud, flowchart shapes, etc.)
- Place UML elements (class, interface, actor, use case, component, package, node)
- Place text labels and freeform line/connector objects with anchor snapping
- Draw directional connectors between services with arrowheads and pull-to-connect from anchor points
- Global connection routing mode (orthogonal or diagonal)
- Right-click context menus on canvas and objects (copy, paste, duplicate, rename, lock/unlock, group/ungroup, z-order, delete)
- Marquee (box) selection for multi-object operations
- Object resize handles with drag sizing
- Inline rename overlay for quick object renaming
- Object grouping and ungrouping
- Object locking to prevent accidental edits
- Z-order controls (bring to front/back, bring forward/backward)
- Service-specific config panels (Lambda runtime/memory, DynamoDB keys, API Gateway protocol, etc.)
- Visual config panels per object type (fill, border, stroke style, font, dimensions)
- Global Terraform config panel (backend type, provider region/profile, version constraints)
- Per-resource Terraform variables panel
- Configurable layout: sidebar position (left/right), toolbar position (top/bottom) via Preferences dialog
- Sidebar and bottom panel modes for the config/properties panel
- Undo/redo with snapshot-based history (50 levels)
- Save/load diagrams to server (persisted via anonymous session) with localStorage fallback
- Export to Terraform via the backend API (downloads ZIP)
- Project settings with multi-environment support
- Keyboard shortcuts: Ctrl+Z/Ctrl+Shift+Z (undo/redo), Delete (remove selected), Escape (deselect)
- Toast notifications for user feedback
- Dark theme throughout

### Testing

154 test files covering:
- 120 property-based test files (fast-check) validating viewport math, element/connector operations, state consistency, undo/redo round-trips, serialization, canvas object CRUD, context menu actions, z-order, grouping, locking, marquee selection, drag sizing, anchor snapping, sidebar/bottom panel behavior, layout preferences, architecture search panel, connection routing, variable configuration, orthogonal line preview, and anchor hit zone behavior
- 33 unit test files for the Zustand store, viewport utilities, icon registry, storage, export, config forms, tool state, hamburger menu, dialogs, bottom panel, element layer, placement preview, visual config, z-order controls, Terraform variables, connection routing, and more
- 1 integration test for Next.js config

## Backend

### Architecture

The backend is organized into layers:

- **Routers** — FastAPI route handlers for diagram CRUD (`/api/diagrams`) and Terraform generation (`/generate/*`)
- **Services** — Business logic including the session manager, IR builder, connection processor, file tree assembler, and IaC code generator
- **Middleware** — Session middleware that manages anonymous cookie-based sessions on every request
- **Persistence** — Repository pattern abstraction with TinyDB (local) and DynamoDB (production) implementations
- **Generators** — HCL/Terraform code generators for each AWS service type

### API Endpoints

#### Diagram CRUD

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/diagrams` | Save a new diagram, returns `{"id": "..."}` |
| `GET` | `/api/diagrams` | List diagram summaries for the current session |
| `GET` | `/api/diagrams/{id}` | Load full diagram state |
| `PUT` | `/api/diagrams/{id}` | Update an existing diagram |
| `DELETE` | `/api/diagrams/{id}` | Delete a diagram (returns 204) |

All diagram endpoints are scoped to the current session via the `session_id` cookie. Cross-session access returns 403.

#### Terraform Generation

#### `GET /api/variable-schemas`

Returns all Terraform variable schemas as JSON, keyed by service type. Used by the frontend to render per-resource variable configuration forms.

#### `POST /generate/json`

Returns the generated Terraform file tree as JSON along with a summary.

#### `POST /generate/zip`

Returns the generated Terraform file tree as a downloadable ZIP archive.

### Example Request Body (Terraform Generation)

```json
{
  "project_name": "my-project",
  "environments": [
    {
      "name": "dev",
      "variables": { "region": "us-east-1" }
    },
    {
      "name": "prod",
      "variables": { "region": "us-west-2" }
    }
  ],
  "resources": [
    {
      "name": "my-function",
      "service_type": "lambda",
      "config": {
        "handler": "index.handler",
        "runtime": "python3.12"
      },
      "terraform_variables": {}
    },
    {
      "name": "my-bucket",
      "service_type": "s3",
      "config": { "versioning": true },
      "terraform_variables": {}
    },
    {
      "name": "my-table",
      "service_type": "dynamodb",
      "config": {
        "hash_key": "id",
        "hash_key_type": "S",
        "billing_mode": "PAY_PER_REQUEST"
      },
      "terraform_variables": {}
    }
  ],
  "connections": [
    {
      "source": "my-function",
      "target": "my-table",
      "connection_type": "reads_from"
    },
    {
      "source": "my-function",
      "target": "my-bucket",
      "connection_type": "writes_to"
    }
  ],
  "global_terraform_config": {
    "backend_type": "local",
    "backend_config": {},
    "provider_region": "us-east-1",
    "provider_profile": null,
    "terraform_version": null,
    "aws_provider_version": null
  }
}
```

### Example JSON Response

```json
{
  "summary": {
    "project_name": "my-project",
    "environment_count": 2,
    "module_count": 3,
    "resource_instance_count": 3,
    "iam_policy_count": 1
  },
  "files": {
    "my-project/environments/dev/main.tf": "...",
    "my-project/modules/lambda/my-function/lambda.tf": "...",
    "my-project/iam-policies/my-function-policy.json": "..."
  }
}
```

## Documentation

Detailed documentation is available in the `docs/` folder:

- `backend-api.md` — API endpoint reference
- `backend-generators.md` — Terraform generator internals
- `backend-models.md` — Pydantic input/output models
- `backend-services.md` — Service layer architecture
- `database.md` — Database schema and storage
- `frontend-components.md` — React component reference
- `frontend-state-and-utils.md` — Zustand stores and utilities
- `persistence.md` — Repository pattern and backends
- `testing.md` — Test strategy and configuration

## Key Features

- Generates valid HCL with consistent two-space indentation
- Wires resource connections automatically (API Gateway → Lambda integrations, Lambda → DynamoDB/S3 IAM policies)
- Produces standalone JSON IAM policy documents in a dedicated `iam-policies/` folder
- Uses Terraform resource references instead of hardcoded values
- Validates input and returns descriptive 422 errors for invalid payloads
- Anonymous cookie-based sessions (no login required, 30-day expiry)
- Diagram persistence with repository pattern (TinyDB for local dev, DynamoDB for production)
- CORS configured for cross-origin frontend/backend development
