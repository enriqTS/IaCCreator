# Implementation Plan: Terraform IaC Generator

## Overview

Build a Python FastAPI backend that transforms a structured JSON architecture description into a complete, modular Terraform file structure for AWS. Implementation follows the pipeline: input validation → IR building → code generation → file tree assembly → output serialization. Uses Pydantic v2 for data models, hypothesis for property-based testing.

## Tasks

- [x] 1. Set up project structure, dependencies, and data models
  - [x] 1.1 Create project directory structure and install dependencies
    - Create `app/` package with `__init__.py`, `main.py` (FastAPI app), `models/`, `generators/`, `services/`
    - Create `tests/` package with `conftest.py`, `test_unit.py`, `test_properties.py`
    - Create `pyproject.toml` or `requirements.txt` with: `fastapi`, `uvicorn`, `pydantic>=2.0`, `hypothesis`, `pytest`
    - _Requirements: 1.1, 1.4_

  - [x] 1.2 Implement input data models (Pydantic schemas)
    - Create `app/models/input_models.py` with `ServiceType` enum, `ResourceConfig`, `ResourceInstance`, `Connection`, `EnvironmentConfig`, `ArchitectureDescription`
    - All fields, validators, and defaults as specified in the design document
    - Add custom validator for DynamoDB requiring `hash_key` in config
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 1.3 Implement Internal Representation (IR) data models
    - Create `app/models/ir_models.py` with `IAMStatement`, `ConnectionIR`, `ResourceInstanceIR`, `ServiceModuleIR`, `EnvironmentIR`, `ProjectIR`, `GeneratedFile`, `GenerationSummary`
    - Define `FileTree = dict[str, str]` type alias
    - _Requirements: 7.1_

  - [x] 1.4 Write unit tests for input validation
    - Test valid payloads with all six service types
    - Test missing required fields return validation errors
    - Test unsupported service type rejection
    - Test DynamoDB custom validator
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. Implement IR Builder
  - [x] 2.1 Implement the IRBuilder service
    - Create `app/services/ir_builder.py` with `IRBuilder.build(input: ArchitectureDescription) -> ProjectIR`
    - Transform validated input into normalized IR tree: group resources by service type into `ServiceModuleIR`, build `EnvironmentIR` with module refs, build `ConnectionIR` list, attach IAM statements to Lambda instances based on connections
    - Validate connections reference existing resource names (raise 422 on invalid)
    - Validate connections between incompatible service types are rejected
    - _Requirements: 7.1, 7.2, 7.3, 8.2, 8.3, 8.4, 9.4_

  - [x] 2.2 Write unit tests for IR Builder
    - Test IR building with a known small input and verify structure
    - Test connection validation rejects non-existent resource names
    - Test connection validation rejects incompatible service type pairs
    - Test Lambda IAM statements are derived from connections
    - _Requirements: 7.1, 8.2, 8.3_

- [x] 3. Implement HCL Renderer
  - [x] 3.1 Implement the HCLRenderer class
    - Create `app/generators/hcl_renderer.py` with `HCLRenderer`
    - Implement `render_resource(block_type, name, attrs) -> str`
    - Implement `render_variable(name, var_type, description, default) -> str`
    - Implement `render_output(name, value, description) -> str`
    - Implement `render_module(name, source, variables) -> str`
    - Implement `render_provider(provider, region) -> str`
    - All output uses two-space indentation, no tabs
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 7.4_

  - [x] 3.2 Write property test for HCL two-space indentation
    - **Property 12: Two-space indentation**
    - **Validates: Requirements 7.4**

  - [x] 3.3 Write unit tests for HCL Renderer
    - Test each render method with known inputs and verify exact HCL output
    - Test nested attributes render correctly
    - Test special characters are properly escaped
    - _Requirements: 5.1, 5.3, 5.4, 5.5_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement Service Generators and Registry
  - [x] 5.1 Implement the ServiceGenerator protocol and registry
    - Create `app/generators/base.py` with `ServiceGenerator` Protocol defining `generate_resource_tf`, `generate_variables_tf`, `generate_outputs_tf`
    - Create `app/generators/registry.py` with `GENERATOR_REGISTRY: dict[ServiceType, ServiceGenerator]`
    - _Requirements: 3.3, 3.4_

  - [x] 5.2 Implement LambdaGenerator
    - Create `app/generators/lambda_generator.py`
    - Generate `aws_lambda_function` resource with `function_name`, `role`, `handler`, `runtime`
    - Generate `iam.tf` with IAM role and policy referencing `file()` to `iam-policies/`
    - Handle Lambda layers with same structure
    - _Requirements: 4.5, 4.6, 5.6, 9.5_

  - [x] 5.3 Implement S3Generator
    - Create `app/generators/s3_generator.py`
    - Generate `aws_s3_bucket` resource with `bucket` attribute
    - Support optional versioning config
    - _Requirements: 5.7_

  - [x] 5.4 Implement DynamoDBGenerator
    - Create `app/generators/dynamodb_generator.py`
    - Generate `aws_dynamodb_table` resource with `name`, `billing_mode`, `hash_key`, and `attribute` block
    - Support optional range key
    - _Requirements: 5.8_

  - [x] 5.5 Implement APIGatewayGenerator
    - Create `app/generators/api_gateway_generator.py`
    - Generate `aws_apigatewayv2_api` resource with `name`, `protocol_type`
    - _Requirements: 5.9_

  - [x] 5.6 Implement CloudWatchGenerator
    - Create `app/generators/cloudwatch_generator.py`
    - Generate `aws_cloudwatch_log_group` resource with `name`
    - Support optional `retention_in_days`
    - _Requirements: 5.10_

  - [x] 5.7 Implement IAMGenerator
    - Create `app/generators/iam_generator.py`
    - Generate IAM role and policy resources
    - _Requirements: 4.5_

  - [x] 5.8 Write property test for service-specific required attributes
    - **Property 10: Service-specific required attributes**
    - **Validates: Requirements 5.6, 5.7, 5.8, 5.9, 5.10**

  - [x] 5.9 Write property test for HCL block attribute completeness
    - **Property 11: HCL block attribute completeness**
    - **Validates: Requirements 5.3, 5.4, 5.5**

- [x] 6. Implement IAM Policy Generator and Connection Processor
  - [x] 6.1 Implement IAMPolicyGenerator
    - Create `app/generators/iam_policy_generator.py`
    - Implement `generate_policy_document(instance: ResourceInstanceIR) -> str` producing valid JSON IAM policy
    - Implement `generate_base_execution_policy(function_name: str) -> str` with CloudWatch Logs permissions
    - Consolidate all permission statements per Lambda into a single JSON document
    - Output follows AWS IAM policy JSON schema: `Version`, `Statement` array with `Effect`, `Action`, `Resource`
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.6, 9.7_

  - [x] 6.2 Implement ConnectionProcessor
    - Create `app/services/connection_processor.py`
    - Process API Gateway → Lambda connections: generate `aws_apigatewayv2_integration` resource
    - Process Lambda → DynamoDB connections: add read/write IAM statements
    - Process Lambda → S3 connections: add S3 access IAM statements
    - Process Lambda → CloudWatch connections: generate log group resource
    - Use Terraform resource references (e.g., `aws_lambda_function.name.arn`) instead of hardcoded values
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 6.3 Write property test for valid IAM policy JSON syntax
    - **Property 19: Valid IAM policy JSON syntax**
    - **Validates: Requirements 9.3**

  - [x] 6.4 Write property test for one consolidated IAM policy per Lambda
    - **Property 18: One consolidated IAM policy per Lambda**
    - **Validates: Requirements 9.2, 9.6, 9.7**

  - [x] 6.5 Write property test for connection-derived IAM policy statements
    - **Property 16: Connection-derived IAM policy statements**
    - **Validates: Requirements 8.2, 8.3, 8.4, 9.4**

  - [x] 6.6 Write property test for API Gateway–Lambda integration generation
    - **Property 15: API Gateway–Lambda integration generation**
    - **Validates: Requirements 8.1**

  - [x] 6.7 Write property test for Terraform references over hardcoded values
    - **Property 17: Terraform references over hardcoded values**
    - **Validates: Requirements 8.5**

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement File Tree Assembler and Code Generator
  - [x] 8.1 Implement FileTreeAssembler
    - Create `app/services/file_tree_assembler.py`
    - Walk `ProjectIR` tree and collect all generated content into `FileTree`
    - Generate environment files: `main.tf` (provider + module blocks), `variables.tf`, `outputs.tf`, `terraform.tfvars`
    - Generate service module root files: `main.tf` (module blocks per instance), `variables.tf`, `outputs.tf`
    - Generate resource instance files: `{service_type}.tf`, `variables.tf`, `outputs.tf`, and `iam.tf` for Lambda
    - Generate IAM policy JSON files in `iam-policies/`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1, 4.2, 4.3, 4.4, 9.1, 9.2_

  - [x] 8.2 Implement CodeGenerator orchestrator
    - Create `app/services/code_generator.py` with `CodeGenerator.generate(project: ProjectIR) -> FileTree`
    - Orchestrate: iterate modules → use registry to get generators → generate per-instance files → run connection processor → run IAM policy generator → assemble file tree
    - _Requirements: 3.3, 3.4, 3.5, 3.6, 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 8.3 Write property test for project-level folder structure
    - **Property 3: Project-level folder structure**
    - **Validates: Requirements 2.1, 2.2, 2.3, 3.1, 3.2, 9.1**

  - [x] 8.4 Write property test for environment file completeness
    - **Property 4: Environment file completeness**
    - **Validates: Requirements 2.4**

  - [x] 8.5 Write property test for environment variable consistency
    - **Property 5: Environment variable consistency**
    - **Validates: Requirements 2.5, 2.7**

  - [x] 8.6 Write property test for environment module references
    - **Property 6: Environment module references**
    - **Validates: Requirements 2.6, 2.8**

  - [x] 8.7 Write property test for service module file structure and content
    - **Property 7: Service module file structure and content**
    - **Validates: Requirements 3.3, 3.4, 3.5, 3.6**

  - [x] 8.8 Write property test for resource instance subfolder structure
    - **Property 8: Resource instance subfolder structure**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**

  - [x] 8.9 Write property test for Lambda iam.tf with file() references
    - **Property 9: Lambda iam.tf with file() references**
    - **Validates: Requirements 4.5, 4.6, 9.5**

  - [x] 8.10 Write property test for AWS provider configuration
    - **Property 20: AWS provider configuration**
    - **Validates: Requirements 5.2**

- [x] 9. Implement Output Serializer and API Endpoints
  - [x] 9.1 Implement OutputSerializer
    - Create `app/services/output_serializer.py`
    - Implement `to_zip(file_tree: FileTree) -> bytes` producing a valid ZIP archive
    - Implement `to_json(file_tree: FileTree, summary: GenerationSummary) -> dict` producing JSON with `files` and `summary` keys
    - _Requirements: 6.2, 6.3, 6.4_

  - [x] 9.2 Implement API endpoints and wire the pipeline
    - In `app/main.py`, create `POST /generate/zip` endpoint returning `application/zip`
    - Create `POST /generate/json` endpoint returning JSON with file tree and summary
    - Wire the full pipeline: validate → build IR → generate → serialize
    - Add error handling: 422 for validation errors (automatic via Pydantic), 500 for generation failures with descriptive messages
    - _Requirements: 1.1, 1.2, 1.3, 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 9.3 Write property test for valid input acceptance
    - **Property 1: Valid input acceptance**
    - **Validates: Requirements 1.1, 1.4**

  - [x] 9.4 Write property test for invalid input error reporting
    - **Property 2: Invalid input error reporting**
    - **Validates: Requirements 1.2**

  - [x] 9.5 Write property test for output format correctness
    - **Property 14: Output format correctness**
    - **Validates: Requirements 6.2, 6.3, 6.4**

- [x] 10. Implement Hypothesis strategies and IR round-trip property test
  - [x] 10.1 Implement shared Hypothesis strategies in conftest.py
    - Create `architecture_description_strategy()` generating random valid `ArchitectureDescription` objects
    - Create `resource_instance_strategy(service_type)` for per-service random instances
    - Create `connection_strategy(resources)` for valid connections between existing resources
    - Ensure strategies produce valid inputs covering all six service types
    - _Requirements: 7.2_

  - [~] 10.2 Write property test for IR serialization round-trip
    - **Property 13: IR serialization round-trip**
    - **Validates: Requirements 7.2, 7.3**

- [ ] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The service generator registry pattern makes adding future cloud providers (GCP, Azure) straightforward
