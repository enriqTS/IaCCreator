"""Variable schemas per service type — defines which Terraform variables each service exposes."""

from app.models.input_models import ServiceType

VARIABLE_SCHEMAS: dict[ServiceType, list[dict]] = {
    ServiceType.LAMBDA: [
        {"name": "function_name", "type": "string", "description": "Name of the Lambda function"},
        {"name": "handler", "type": "string", "description": "Lambda function handler"},
        {"name": "runtime", "type": "string", "description": "Lambda function runtime"},
        {"name": "memory_size", "type": "number", "description": "Memory size in MB", "default": 128},
        {"name": "timeout", "type": "number", "description": "Timeout in seconds", "default": 3},
    ],
    ServiceType.S3: [
        {"name": "bucket_name", "type": "string", "description": "Name of the S3 bucket"},
        {"name": "versioning_enabled", "type": "bool", "description": "Enable versioning", "default": False},
    ],
    ServiceType.DYNAMODB: [
        {"name": "table_name", "type": "string", "description": "Name of the DynamoDB table"},
        {"name": "billing_mode", "type": "string", "description": "Billing mode", "default": "PAY_PER_REQUEST"},
        {"name": "hash_key", "type": "string", "description": "Hash key attribute name"},
        {"name": "hash_key_type", "type": "string", "description": "Hash key attribute type", "default": "S"},
        {"name": "range_key", "type": "string", "description": "Range key attribute name"},
        {"name": "range_key_type", "type": "string", "description": "Range key attribute type", "default": "S"},
    ],
    ServiceType.API_GATEWAY: [
        {"name": "api_name", "type": "string", "description": "Name of the API Gateway"},
        {"name": "protocol_type", "type": "string", "description": "Protocol type", "default": "HTTP"},
    ],
    ServiceType.CLOUDWATCH: [
        {"name": "log_group_name", "type": "string", "description": "Name of the CloudWatch log group"},
        {"name": "retention_in_days", "type": "number", "description": "Log retention in days", "default": 30},
    ],
}
