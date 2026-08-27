# Backend Generators

`app/generators/` renders Terraform/HCL from the IR. Every registered service has a dedicated config model and a generator registered in `GENERATOR_REGISTRY`.

## Generator contract and registry

`ServiceGenerator` in `app/generators/base.py` defines `generate_resource_tf`, `generate_variables_tf`, and `generate_outputs_tf`. `GENERATOR_REGISTRY` maps `ServiceType` values to generator instances. Consult that registry as the authoritative list rather than maintaining a duplicate list here.

The registry currently covers core services (including EventBridge), compute, analytics, business applications, databases, developer tools, end-user computing, frontend/web/mobile, games, and machine-learning services. Machine-learning coverage includes Bedrock, SageMaker, Amazon Q, Bedrock Agent, Guardrail, Knowledge Base, and AgentCore. Icon-only `ServiceType` values intentionally have no generator.

API Gateway is split across `app/generators/api_gateway/`: API, routes, integrations, stages, authorizers, domains, VPC links, API keys, and outputs each have focused renderers. `api_gateway_generator.py` remains the registry-facing facade.

## Rendering and schemas

`HCLRenderer` produces Terraform resources, variables, outputs, modules, and providers with two-space indentation. It formats Terraform references rather than quoting them and renders nested values as HCL blocks or collections where appropriate.

Variable schemas are not a hand-maintained `VARIABLE_SCHEMAS` dictionary. Each service's config model uses `TerraformField` metadata; `BaseServiceConfig.get_variable_schema()` derives the schema used by validation, the API endpoint, and the frontend. Metadata includes labels, descriptions, requiredness, defaults, options, validation, groups, and conditional visibility.

`schema_validator.py` validates submitted typed configs against those derived schemas, including closed option sets and conditional fields.

## Project assembly

`FileTreeAssembler` writes environment configuration under:

```
{project}/environments/{environment}/
```

and per-instance modules under:

```
{project}/modules/{category}/{service}/{instance}/
```

Each instance gets its resource, variable, and output files. A service whose config model owns an execution role also gets `iam.tf` and `{project}/iam-policies/{instance}-policy.json`; this is not Lambda-specific.

The assembler uses `module_arguments.py`, `module_paths.py`, and `service_category_map.py` to keep environment module wiring and categorized paths consistent. `TfvarsGenerator` creates environment variable declarations and values; `GlobalConfigGenerator` writes `backend.tf`, `provider.tf`, and `versions.tf`.

## Connection-generated Terraform

Connection handlers return `ConnectionContribution`: module inputs, module outputs, module-owned resources, and IAM grants. `FileTreeAssembler` folds those into the owning instance module and passes cross-module values through environment module calls. List-valued network inputs remain typed HCL collections; explicit IDs are fallback defaults, while managed Subnet and Security Group connections override module-call inputs with Terraform references. Network Firewall emits one dynamic subnet mapping per selected Subnet, and Client VPN emits network associations for selected Subnets. This keeps connection resources in their owning module and avoids Terraform dependency cycles.
