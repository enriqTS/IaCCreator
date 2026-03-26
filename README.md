# IaCreator

A visual AWS architecture diagram editor with Terraform IaC generation.

Design your cloud architecture by placing AWS service nodes on an infinite canvas, connecting them, configuring service-specific properties, and exporting the result as a production-ready Terraform project — all from the browser.

The project consists of two parts:
- **Frontend** — Next.js 16 visual diagram editor with pan/zoom canvas, drag-and-drop service placement, and real-time configuration
- **Backend** — FastAPI service that transforms architecture descriptions into modular Terraform file structures

## Supported AWS Services

- Lambda (including Lambda Layers)
- S3
- API Gateway (v2)
- DynamoDB
- IAM
- CloudWatch

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
│   └── cloudwatch/
│       └── ...
└── iam-policies/
    └── my-function-policy.json
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20.9+

### Backend

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The diagram editor will be available at `http://localhost:3000`.

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
- HTML5 Canvas for grid/connectors, DOM overlay for interactive service nodes
- Vitest + fast-check for unit and property-based testing

### Features

- Infinite pan/zoom canvas with dot grid background
- Place AWS service nodes from a categorized picker (200+ services, 26 categories)
- Draw directional connectors between services with arrowheads
- Service-specific config panels (Lambda runtime/memory, DynamoDB keys, API Gateway protocol, etc.)
- Undo/redo with snapshot-based history (50 levels)
- Save/load diagrams to localStorage
- Export to Terraform via the backend API (downloads ZIP)
- Project settings with multi-environment support
- Keyboard shortcuts: Ctrl+Z/Ctrl+Shift+Z (undo/redo), Delete (remove selected), Escape (deselect)
- Dark theme throughout

### Testing

156 tests across 14 files covering:
- 13 property-based tests (fast-check, 100+ iterations each) validating viewport math, element/connector operations, state consistency, undo/redo round-trips, and serialization
- Unit tests for the Zustand store, viewport utilities, icon registry, storage, export, config forms, tool state, hamburger menu, and dialogs

## Backend

### API Endpoints

### `POST /generate/json`

Returns the generated Terraform file tree as JSON along with a summary.

### `POST /generate/zip`

Returns the generated Terraform file tree as a downloadable ZIP archive.

### Example Request Body

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
      }
    },
    {
      "name": "my-bucket",
      "service_type": "s3",
      "config": { "versioning": true }
    },
    {
      "name": "my-table",
      "service_type": "dynamodb",
      "config": {
        "hash_key": "id",
        "hash_key_type": "S",
        "billing_mode": "PAY_PER_REQUEST"
      }
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
  ]
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

## Key Features

- Generates valid HCL with consistent two-space indentation
- Wires resource connections automatically (API Gateway → Lambda integrations, Lambda → DynamoDB/S3 IAM policies)
- Produces standalone JSON IAM policy documents in a dedicated `iam-policies/` folder
- Uses Terraform resource references instead of hardcoded values
- Validates input and returns descriptive 422 errors for invalid payloads
