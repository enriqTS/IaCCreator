# Requirements Document

## Introduction

The Terraform IaC Generator is a backend engine that takes a visual cloud architecture description (as a structured input) and generates a complete, modular Terraform file structure for AWS. Unlike monolithic Terraform files, the engine produces a well-organized folder hierarchy with per-service modules, per-resource subfolders, and per-environment configurations. The initial scope covers six AWS services: Lambda, S3, API Gateway, DynamoDB, IAM, and CloudWatch. The backend is built with Python FastAPI and will later be consumed by a Next.js frontend.

## Glossary

- **Generator_Engine**: The core backend system responsible for transforming an architecture description into Terraform files
- **Architecture_Description**: A structured JSON input representing the user's cloud architecture, including services, resources, connections, environments, and project metadata
- **Project**: A named collection of environments and modules representing a single cloud architecture; the project name becomes the root folder name
- **Environment**: A deployment target (e.g., dev, staging, prod) with its own set of Terraform variable values
- **Module**: A Terraform module folder representing a single AWS service type (e.g., lambda, s3, dynamodb)
- **Resource_Instance**: A specific named resource within a module (e.g., a specific Lambda function or S3 bucket), each getting its own subfolder
- **Terraform_File_Structure**: The complete generated folder hierarchy containing environments, modules, resource instance subfolders, and all associated .tf and .tfvars files
- **Service_Type**: One of the supported AWS service categories: Lambda, S3, API Gateway, DynamoDB, IAM, CloudWatch
- **Inline_IAM**: IAM permission definitions co-located within the resource instance folder rather than in a centralized IAM module
- **IAM_Policy_Folder**: A top-level folder named `iam-policies` at the project root, containing reusable JSON IAM policy documents
- **JSON_Policy_Document**: A standalone JSON file defining an IAM policy, stored in the IAM_Policy_Folder and referenced by Terraform resources using the `file()` function
- **Lambda_Layer**: A Lambda layer resource, structured identically to a Lambda function with its own subfolder within the lambda module

## Requirements

### Requirement 1: Accept Architecture Description Input

**User Story:** As a developer, I want to submit a structured architecture description to the API, so that the system can generate Terraform code from it.

#### Acceptance Criteria

1. WHEN an Architecture_Description is submitted via HTTP POST, THE Generator_Engine SHALL validate the input against a defined JSON schema
2. IF the Architecture_Description is missing required fields, THEN THE Generator_Engine SHALL return a 422 response with a list of validation errors identifying each missing or invalid field
3. IF the Architecture_Description references an unsupported Service_Type, THEN THE Generator_Engine SHALL return a 422 response identifying the unsupported service
4. THE Generator_Engine SHALL accept Architecture_Descriptions containing any combination of the six supported Service_Types: Lambda, S3, API Gateway, DynamoDB, IAM, CloudWatch

### Requirement 2: Generate Project Root and Environment Structure

**User Story:** As a developer, I want the generator to create a proper folder structure with environment-specific configurations, so that I can manage multiple deployment targets independently.

#### Acceptance Criteria

1. WHEN a valid Architecture_Description is processed, THE Generator_Engine SHALL create a root folder named after the Project name
2. WHEN a valid Architecture_Description is processed, THE Generator_Engine SHALL create an `environments` folder containing one subfolder per defined Environment
3. WHEN a valid Architecture_Description is processed, THE Generator_Engine SHALL create an `iam-policies` folder at the project root level alongside `environments` and `modules`
4. THE Generator_Engine SHALL generate four files in each Environment subfolder: `main.tf`, `variables.tf`, `outputs.tf`, and `terraform.tfvars`
5. THE Generator_Engine SHALL populate `terraform.tfvars` with environment-specific variable values derived from the Architecture_Description
6. THE Generator_Engine SHALL populate `main.tf` in each Environment with module references pointing to the generated modules
7. THE Generator_Engine SHALL populate `variables.tf` in each Environment with variable declarations matching the keys used in `terraform.tfvars`
8. THE Generator_Engine SHALL populate `outputs.tf` in each Environment with output declarations exposing key resource attributes from the referenced modules

### Requirement 3: Generate Service Module Structure

**User Story:** As a developer, I want each AWS service to have its own module folder with a consistent structure, so that the Terraform code is modular and maintainable.

#### Acceptance Criteria

1. WHEN a valid Architecture_Description is processed, THE Generator_Engine SHALL create a `modules` folder at the project root level
2. THE Generator_Engine SHALL create one subfolder inside `modules` for each Service_Type referenced in the Architecture_Description
3. THE Generator_Engine SHALL generate three files at the service module root level: `main.tf`, `variables.tf`, and `outputs.tf`
4. THE Generator_Engine SHALL populate the service module `main.tf` with Terraform module blocks referencing each Resource_Instance subfolder within that service
5. THE Generator_Engine SHALL populate the service module `variables.tf` with variable declarations required to configure all Resource_Instances within that service
6. THE Generator_Engine SHALL populate the service module `outputs.tf` with output declarations aggregating outputs from all Resource_Instances within that service

### Requirement 4: Generate Per-Resource Instance Subfolders

**User Story:** As a developer, I want each individual resource (e.g., each Lambda function, each S3 bucket) to have its own subfolder, so that resource definitions are isolated and easy to manage.

#### Acceptance Criteria

1. WHEN a Service_Type contains one or more Resource_Instances, THE Generator_Engine SHALL create a named subfolder for each Resource_Instance inside the service module folder
2. THE Generator_Engine SHALL name each Resource_Instance subfolder using the user-defined resource name from the Architecture_Description
3. THE Generator_Engine SHALL generate a main resource definition file in each Resource_Instance subfolder, named after the Service_Type (e.g., `lambda.tf` for Lambda, `s3.tf` for S3, `dynamodb.tf` for DynamoDB)
4. THE Generator_Engine SHALL generate `variables.tf` and `outputs.tf` files in each Resource_Instance subfolder
5. WHEN a Resource_Instance is of Service_Type Lambda, THE Generator_Engine SHALL generate an `iam.tf` file in the Resource_Instance subfolder containing Inline_IAM role and policy definitions that reference corresponding JSON_Policy_Documents from the IAM_Policy_Folder using the `file()` function
6. WHEN a Resource_Instance is of Service_Type Lambda and is designated as a Lambda_Layer, THE Generator_Engine SHALL generate the subfolder with the same structure as a Lambda function subfolder

### Requirement 5: Generate Valid Terraform HCL Code

**User Story:** As a developer, I want the generated Terraform files to contain valid HCL syntax, so that I can run `terraform init` and `terraform plan` without syntax errors.

#### Acceptance Criteria

1. THE Generator_Engine SHALL produce all `.tf` files using valid HashiCorp Configuration Language (HCL) syntax
2. THE Generator_Engine SHALL use the AWS provider with a configurable region in each Environment `main.tf`
3. THE Generator_Engine SHALL generate `variable` blocks with `description` and `type` attributes for every variable declaration
4. THE Generator_Engine SHALL generate `output` blocks with `description` and `value` attributes for every output declaration
5. THE Generator_Engine SHALL generate `module` blocks with `source` paths that correctly reference the relative file system location of each module and Resource_Instance subfolder
6. WHEN generating Lambda resource definitions, THE Generator_Engine SHALL include `aws_lambda_function` resource blocks with required attributes: `function_name`, `role`, `handler`, `runtime`
7. WHEN generating S3 resource definitions, THE Generator_Engine SHALL include `aws_s3_bucket` resource blocks with required attributes: `bucket`
8. WHEN generating DynamoDB resource definitions, THE Generator_Engine SHALL include `aws_dynamodb_table` resource blocks with required attributes: `name`, `billing_mode`, `hash_key`, and at least one `attribute` block
9. WHEN generating API Gateway resource definitions, THE Generator_Engine SHALL include `aws_apigatewayv2_api` resource blocks with required attributes: `name`, `protocol_type`
10. WHEN generating CloudWatch resource definitions, THE Generator_Engine SHALL include `aws_cloudwatch_log_group` resource blocks with required attributes: `name`

### Requirement 6: Return Generated Output via API

**User Story:** As a developer, I want to receive the generated Terraform structure as a downloadable archive or structured response, so that I can use it in my local development workflow.

#### Acceptance Criteria

1. WHEN Terraform generation completes successfully, THE Generator_Engine SHALL return a response containing the complete Terraform_File_Structure
2. THE Generator_Engine SHALL support returning the Terraform_File_Structure as a ZIP archive with `application/zip` content type
3. THE Generator_Engine SHALL support returning the Terraform_File_Structure as a JSON response containing file paths and their contents
4. WHEN generation completes, THE Generator_Engine SHALL include a summary in the response listing the count of environments, modules, and resource instances generated
5. IF an internal error occurs during generation, THEN THE Generator_Engine SHALL return a 500 response with an error message describing the failure point

### Requirement 7: Terraform Code Serialization (Round-Trip)

**User Story:** As a developer, I want the system to reliably serialize and deserialize Terraform structures, so that the internal representation and generated output remain consistent.

#### Acceptance Criteria

1. THE Generator_Engine SHALL maintain an internal representation (IR) of the Terraform_File_Structure as a Python data model
2. FOR ALL valid Architecture_Descriptions, serializing the IR to HCL file contents and then parsing those contents back into an IR SHALL produce an equivalent data structure (round-trip property)
3. THE Generator_Engine SHALL serialize the IR to the Terraform_File_Structure without data loss for all supported Service_Types
4. THE Generator_Engine SHALL format generated HCL files with consistent two-space indentation

### Requirement 8: Support Resource Connections and References

**User Story:** As a developer, I want the generated Terraform code to reflect connections between resources (e.g., API Gateway triggering Lambda), so that the infrastructure is properly wired.

#### Acceptance Criteria

1. WHEN the Architecture_Description defines a connection between an API Gateway Resource_Instance and a Lambda Resource_Instance, THE Generator_Engine SHALL generate an `aws_apigatewayv2_integration` resource linking the two
2. WHEN the Architecture_Description defines a connection between a Lambda Resource_Instance and a DynamoDB Resource_Instance, THE Generator_Engine SHALL generate a JSON_Policy_Document in the IAM_Policy_Folder granting the function read/write access to the specified table, and reference that policy in the Lambda's `iam.tf`
3. WHEN the Architecture_Description defines a connection between a Lambda Resource_Instance and an S3 Resource_Instance, THE Generator_Engine SHALL generate a JSON_Policy_Document in the IAM_Policy_Folder granting the function access to the specified bucket, and reference that policy in the Lambda's `iam.tf`
4. WHEN the Architecture_Description defines a connection between a Lambda Resource_Instance and a CloudWatch Resource_Instance, THE Generator_Engine SHALL generate a `aws_cloudwatch_log_group` resource with a name derived from the Lambda function name
5. THE Generator_Engine SHALL use Terraform resource references (e.g., `aws_lambda_function.name.arn`) instead of hardcoded values when wiring connected resources


### Requirement 9: Generate JSON IAM Policy Files

**User Story:** As a developer, I want IAM policies generated as standalone JSON files in a dedicated folder, so that I have better visibility and control over IAM permissions without them being buried inline in Terraform code.

#### Acceptance Criteria

1. WHEN a valid Architecture_Description is processed, THE Generator_Engine SHALL create an `iam-policies` folder at the project root level alongside `environments` and `modules`
2. WHEN a Lambda Resource_Instance requires IAM permissions, THE Generator_Engine SHALL generate a JSON_Policy_Document in the IAM_Policy_Folder named using the pattern `{resource_instance_name}-policy.json`
3. THE Generator_Engine SHALL produce JSON_Policy_Documents using valid AWS IAM policy JSON syntax, including `Version`, `Statement`, `Effect`, `Action`, and `Resource` fields
4. WHEN a Lambda Resource_Instance has connections to other resources, THE Generator_Engine SHALL generate a JSON_Policy_Document containing IAM statements scoped to the connected resources
5. THE Generator_Engine SHALL reference JSON_Policy_Documents from the Lambda Resource_Instance `iam.tf` using the Terraform `file()` function with a relative path to the IAM_Policy_Folder
6. WHEN multiple connections exist for a single Lambda Resource_Instance, THE Generator_Engine SHALL consolidate all permission statements into a single JSON_Policy_Document for that Resource_Instance
7. THE Generator_Engine SHALL generate a base Lambda execution role JSON_Policy_Document granting CloudWatch Logs permissions for every Lambda Resource_Instance
