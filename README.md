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
- Tailwind CSS 4 with shadcn/ui and Radix UI primitives
- Zustand for state management
- Lucide React for icons
- HTML5 Canvas for grid/connectors, DOM overlay for interactive service nodes and canvas objects
- Vitest + fast-check for unit and property-based testing

### Architecture

The frontend is a single-page application organized into clear layers:

- **App** — Next.js App Router entry point (single route serving the diagram editor)
- **Components** — React components for the canvas, service nodes, config panels, toolbars, and UI primitives
- **Store** — Zustand stores managing diagram state (nodes, connections, selection, viewport transforms)
- **Hooks** — Custom React hooks for canvas interactions (pan, zoom, drag-and-drop, resize)
- **Utils** — Pure utility functions for geometry, HCL formatting, coordinate transforms, and hit-testing
- **Types** — Shared TypeScript interfaces for nodes, connections, service configs, and canvas objects
- **Data** — Static AWS service definitions, icon mappings, and default configurations



## Backend

### Tech Stack

- Python 3.14+ with FastAPI and Uvicorn
- Pydantic v2 for request/response validation
- TinyDB for local persistence, DynamoDB (via Boto3) for production
- Pytest + Hypothesis for unit and property-based testing
- HTTPX for async test client

### Architecture

The backend is organized into layers:

- **Routers** — FastAPI route handlers for diagram CRUD (`/api/diagrams`) and Terraform generation (`/generate/*`)
- **Services** — Business logic including the session manager, IR builder, connection processor, file tree assembler, and IaC code generator
- **Middleware** — Session middleware that manages anonymous cookie-based sessions on every request
- **Persistence** — Repository pattern abstraction with TinyDB (local) and DynamoDB (production) implementations
- **Generators** — HCL/Terraform code generators for each AWS service type



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
