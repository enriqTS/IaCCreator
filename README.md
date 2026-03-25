# IaCreator

A Python FastAPI backend that transforms a structured JSON architecture description into a complete, modular Terraform file structure for AWS.

Submit a JSON payload describing your cloud architecture — services, connections, environments — and get back a ready-to-use Terraform project with per-service modules, per-resource subfolders, and per-environment configurations.

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

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run the Server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Run Tests

```bash
pytest
```

## API Endpoints

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
