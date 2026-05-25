"""Property-based tests for compute & container service generators.

Feature: compute-services-generators
Uses Hypothesis to verify universal correctness properties across all
new compute/container generators and the pipeline skip behavior.
"""

from hypothesis import given, settings, strategies as st

from app.generators.registry import GENERATOR_REGISTRY
from app.generators.service_category_map import get_category
from app.models.input_models import ResourceConfig, ServiceType
from app.models.ir_models import (
    EnvironmentIR,
    ProjectIR,
    ResourceInstanceIR,
    ServiceModuleIR,
)
from app.services.file_tree_assembler import FileTreeAssembler


# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------

_resource_name_st = st.from_regex(r"[a-z][a-z0-9\-]{0,14}", fullmatch=True)

# The 9 full-generator compute/container service types
FULL_GENERATOR_SERVICES = [
    ServiceType.EC2,
    ServiceType.ECS,
    ServiceType.EKS,
    ServiceType.ELASTIC_BEANSTALK,
    ServiceType.APP_RUNNER,
    ServiceType.BATCH,
    ServiceType.EC2_IMAGE_BUILDER,
    ServiceType.LIGHTSAIL,
    ServiceType.ECR,
]

# The 30 icon-only service types
ICON_ONLY_SERVICES = [
    ServiceType.APPLICATION_AUTO_SCALING,
    ServiceType.BOTTLEROCKET,
    ServiceType.COMPUTE_OPTIMIZER,
    ServiceType.EC2_AUTO_SCALING,
    ServiceType.ELASTIC_FABRIC_ADAPTER,
    ServiceType.FARGATE,
    ServiceType.GENOMICS_CLI,
    ServiceType.LOCAL_ZONES,
    ServiceType.NICE_DCV,
    ServiceType.NICE_ENGINFRAME,
    ServiceType.NITRO_ENCLAVES,
    ServiceType.OUTPOSTS_FAMILY,
    ServiceType.OUTPOSTS_RACK,
    ServiceType.OUTPOSTS_SERVERS,
    ServiceType.PARALLELCLUSTER,
    ServiceType.SERVERLESS_APPLICATION_REPOSITORY,
    ServiceType.SIMSPACE_WEAVER,
    ServiceType.THINKBOX_DEADLINE,
    ServiceType.THINKBOX_FROST,
    ServiceType.THINKBOX_KRAKATOA,
    ServiceType.THINKBOX_SEQUOIA,
    ServiceType.THINKBOX_STOKE,
    ServiceType.THINKBOX_XMESH,
    ServiceType.VMWARE_CLOUD_ON_AWS,
    ServiceType.WAVELENGTH,
    ServiceType.ECS_ANYWHERE,
    ServiceType.EKS_ANYWHERE,
    ServiceType.EKS_CLOUD,
    ServiceType.EKS_DISTRO,
    ServiceType.RED_HAT_OPENSHIFT,
]


def _minimal_config_for(service_type: ServiceType) -> ResourceConfig:
    """Return a minimal ResourceConfig with all optional fields as None."""
    return ResourceConfig()


def _make_instance(name: str, service_type: ServiceType, config: ResourceConfig) -> ResourceInstanceIR:
    return ResourceInstanceIR(name=name, service_type=service_type, config=config)


# ---------------------------------------------------------------------------
# Property 1: Generator protocol compliance and non-empty output
# Feature: compute-services-generators, Property 1
# **Validates: Requirements 2.1, 4.1, 6.1, 8.1, 10.1, 12.1, 14.1, 16.1, 18.1, 19.1, 19.2**
# ---------------------------------------------------------------------------

@given(
    service_type=st.sampled_from(list(GENERATOR_REGISTRY.keys())),
    name=_resource_name_st,
)
@settings(max_examples=100)
def test_property_1_generator_protocol_compliance_and_non_empty_output(service_type, name):
    """Property 1: For any service type in GENERATOR_REGISTRY, the generator
    produces non-empty strings from generate_resource_tf, generate_variables_tf,
    and generate_outputs_tf when given a valid ResourceInstanceIR.
    """
    config = _minimal_config_for(service_type)
    instance = _make_instance(name, service_type, config)
    generator = GENERATOR_REGISTRY[service_type]

    resource_tf = generator.generate_resource_tf(instance)
    variables_tf = generator.generate_variables_tf(instance)
    outputs_tf = generator.generate_outputs_tf(instance)

    assert isinstance(resource_tf, str) and len(resource_tf) > 0, (
        f"generate_resource_tf returned empty for {service_type.value}"
    )
    assert isinstance(variables_tf, str) and len(variables_tf) > 0, (
        f"generate_variables_tf returned empty for {service_type.value}"
    )
    assert isinstance(outputs_tf, str) and len(outputs_tf) > 0, (
        f"generate_outputs_tf returned empty for {service_type.value}"
    )


# ---------------------------------------------------------------------------
# Property 2: Conditional config field inclusion
# Feature: compute-services-generators, Property 2
# **Validates: Requirements 2.3, 4.5, 4.6, 6.3, 6.4, 8.4, 8.5, 12.3, 12.4, 18.3, 18.4, 19.3**
# ---------------------------------------------------------------------------

# Mapping: service_type -> list of (config_field_name, expected_var_reference)
# Only services with optional config fields are included.
OPTIONAL_FIELD_MAP: dict[ServiceType, list[tuple[str, str]]] = {
    ServiceType.EC2: [
        ("key_name", "var.key_name"),
    ],
    ServiceType.ECS: [
        ("ecs_launch_type", "var.ecs_launch_type"),
        ("ecs_desired_count", "var.ecs_desired_count"),
    ],
    ServiceType.EKS: [
        ("eks_version", "var.eks_version"),
        ("eks_endpoint_public_access", "var.eks_endpoint_public_access"),
    ],
    ServiceType.ELASTIC_BEANSTALK: [
        ("eb_solution_stack_name", "var.eb_solution_stack_name"),
        ("eb_tier", "var.eb_tier"),
    ],
    ServiceType.BATCH: [
        ("batch_compute_environment_type", "var.batch_compute_environment_type"),
        ("batch_max_vcpus", "var.batch_max_vcpus"),
    ],
    ServiceType.ECR: [
        ("ecr_image_tag_mutability", "var.ecr_image_tag_mutability"),
        ("ecr_scan_on_push", "var.ecr_scan_on_push"),
    ],
    # App Runner, EC2 Image Builder, Lightsail have no optional fields
}

# Services that have optional fields (used for sampling)
_SERVICES_WITH_OPTIONAL_FIELDS = list(OPTIONAL_FIELD_MAP.keys())

# Sample values for optional config fields by type
_OPTIONAL_FIELD_VALUES: dict[str, object] = {
    "key_name": "my-key",
    "ecs_launch_type": "FARGATE",
    "ecs_desired_count": 2,
    "eks_version": "1.28",
    "eks_endpoint_public_access": True,
    "eb_solution_stack_name": "64bit Amazon Linux 2 v3.5.0 running Python 3.8",
    "eb_tier": "WebServer",
    "batch_compute_environment_type": "MANAGED",
    "batch_max_vcpus": 16,
    "ecr_image_tag_mutability": "IMMUTABLE",
    "ecr_scan_on_push": True,
}


@st.composite
def _config_with_random_optional_fields(draw):
    """Generate a (ServiceType, ResourceConfig, set_fields, unset_fields) tuple.

    For a randomly chosen service with optional fields, randomly set/unset
    each optional field.
    """
    service_type = draw(st.sampled_from(_SERVICES_WITH_OPTIONAL_FIELDS))
    fields = OPTIONAL_FIELD_MAP[service_type]

    # Generate a bitmask for which fields to set (at least one combination)
    flags = draw(st.lists(
        st.booleans(),
        min_size=len(fields),
        max_size=len(fields),
    ))

    config_kwargs: dict = {}
    set_fields: list[tuple[str, str]] = []
    unset_fields: list[tuple[str, str]] = []

    for (field_name, var_ref), should_set in zip(fields, flags):
        if should_set:
            config_kwargs[field_name] = _OPTIONAL_FIELD_VALUES[field_name]
            set_fields.append((field_name, var_ref))
        else:
            unset_fields.append((field_name, var_ref))

    config = ResourceConfig(**config_kwargs)
    return service_type, config, set_fields, unset_fields


@given(
    data=_config_with_random_optional_fields(),
    name=_resource_name_st,
)
@settings(max_examples=100)
def test_property_2_conditional_config_field_inclusion(data, name):
    """Property 2: When an optional config field is None, its var reference
    does NOT appear in resource_tf output. When set, it DOES appear.
    """
    service_type, config, set_fields, unset_fields = data
    instance = _make_instance(name, service_type, config)
    generator = GENERATOR_REGISTRY[service_type]
    resource_tf = generator.generate_resource_tf(instance)

    for field_name, var_ref in set_fields:
        assert var_ref in resource_tf, (
            f"Expected '{var_ref}' in resource_tf for {service_type.value} "
            f"when {field_name} is set, but not found.\nHCL:\n{resource_tf}"
        )

    for field_name, var_ref in unset_fields:
        assert var_ref not in resource_tf, (
            f"Expected '{var_ref}' NOT in resource_tf for {service_type.value} "
            f"when {field_name} is None, but it was found.\nHCL:\n{resource_tf}"
        )


# ---------------------------------------------------------------------------
# Property 3: Required Terraform blocks per service
# Feature: compute-services-generators, Property 3
# **Validates: Requirements 2.2, 2.4, 2.5, 4.2-4.4, 4.7, 4.8, 6.2, 6.5, 6.6,
#   8.2, 8.3, 8.6, 8.7, 10.2-10.5, 12.2, 12.5, 12.6, 14.2-14.4,
#   16.2-16.4, 18.2, 18.5, 18.6**
# ---------------------------------------------------------------------------

# Expected blocks per service: (resource_type_strings, variable_names, output_names)
EXPECTED_BLOCKS: dict[ServiceType, tuple[list[str], list[str], list[str]]] = {
    ServiceType.EC2: (
        ['resource "aws_instance"'],
        ["instance_name", "ami", "instance_type"],
        ["instance_id", "public_ip"],
    ),
    ServiceType.ECS: (
        [
            'resource "aws_ecs_cluster"',
            'resource "aws_ecs_task_definition"',
            'resource "aws_ecs_service"',
        ],
        ["cluster_name", "task_family", "ecs_cpu", "ecs_memory"],
        ["cluster_arn", "service_name"],
    ),
    ServiceType.EKS: (
        ['resource "aws_eks_cluster"'],
        ["cluster_name", "cluster_role_arn", "subnet_ids"],
        ["cluster_arn", "cluster_endpoint", "cluster_name"],
    ),
    ServiceType.ELASTIC_BEANSTALK: (
        [
            'resource "aws_elastic_beanstalk_application"',
            'resource "aws_elastic_beanstalk_environment"',
        ],
        ["application_name", "environment_name"],
        ["application_name", "environment_endpoint"],
    ),
    ServiceType.APP_RUNNER: (
        ['resource "aws_apprunner_service"'],
        ["service_name", "image_identifier"],
        ["service_arn", "service_url"],
    ),
    ServiceType.BATCH: (
        ['resource "aws_batch_compute_environment"'],
        ["compute_environment_name", "service_role_arn"],
        ["compute_environment_arn", "compute_environment_name"],
    ),
    ServiceType.EC2_IMAGE_BUILDER: (
        ['resource "aws_imagebuilder_image_pipeline"'],
        ["pipeline_name", "image_recipe_arn", "infrastructure_configuration_arn"],
        ["pipeline_arn"],
    ),
    ServiceType.LIGHTSAIL: (
        ['resource "aws_lightsail_instance"'],
        ["instance_name", "blueprint_id", "bundle_id", "availability_zone"],
        ["instance_arn", "instance_name"],
    ),
    ServiceType.ECR: (
        ['resource "aws_ecr_repository"'],
        ["repository_name"],
        ["repository_arn", "repository_url"],
    ),
}


@given(
    service_type=st.sampled_from(FULL_GENERATOR_SERVICES),
    name=_resource_name_st,
)
@settings(max_examples=100)
def test_property_3_required_terraform_blocks_per_service(service_type, name):
    """Property 3: For each full-generator service, the output contains all
    expected resource type strings, variable block names, and output block names.
    """
    config = _minimal_config_for(service_type)
    instance = _make_instance(name, service_type, config)
    generator = GENERATOR_REGISTRY[service_type]

    resource_tf = generator.generate_resource_tf(instance)
    variables_tf = generator.generate_variables_tf(instance)
    outputs_tf = generator.generate_outputs_tf(instance)

    expected_resources, expected_vars, expected_outputs = EXPECTED_BLOCKS[service_type]

    for res_str in expected_resources:
        assert res_str in resource_tf, (
            f"Expected '{res_str}' in resource_tf for {service_type.value}.\n"
            f"HCL:\n{resource_tf}"
        )

    for var_name in expected_vars:
        assert f'variable "{var_name}"' in variables_tf, (
            f"Expected 'variable \"{var_name}\"' in variables_tf for {service_type.value}.\n"
            f"HCL:\n{variables_tf}"
        )

    for out_name in expected_outputs:
        assert f'output "{out_name}"' in outputs_tf, (
            f"Expected 'output \"{out_name}\"' in outputs_tf for {service_type.value}.\n"
            f"HCL:\n{outputs_tf}"
        )


# ---------------------------------------------------------------------------
# Property 4: Icon-only services excluded from generator registry
# Feature: compute-services-generators, Property 4
# **Validates: Requirements 20.34, 20.35**
# ---------------------------------------------------------------------------

@given(service_type=st.sampled_from(ICON_ONLY_SERVICES))
@settings(max_examples=100)
def test_property_4_icon_only_services_excluded_from_registry(service_type):
    """Property 4: No icon-only service type has an entry in GENERATOR_REGISTRY."""
    assert service_type not in GENERATOR_REGISTRY, (
        f"Icon-only service {service_type.value} should NOT be in GENERATOR_REGISTRY"
    )


# ---------------------------------------------------------------------------
# Property 5: Pipeline skip behavior for mixed service types
# Feature: compute-services-generators, Property 5
# **Validates: Requirements 21.1, 21.2, 21.3**
# ---------------------------------------------------------------------------

@st.composite
def _mixed_project_ir(draw):
    """Generate a ProjectIR with a mix of full-generator and icon-only resources.

    Ensures at least one full-generator and at least one icon-only resource.
    """
    # Pick 1-3 full-generator services
    full_services = draw(st.lists(
        st.sampled_from(FULL_GENERATOR_SERVICES),
        min_size=1,
        max_size=3,
        unique=True,
    ))
    # Pick 1-3 icon-only services
    icon_services = draw(st.lists(
        st.sampled_from(ICON_ONLY_SERVICES),
        min_size=1,
        max_size=3,
        unique=True,
    ))

    all_services = full_services + icon_services
    modules = []
    all_module_refs = []

    for i, svc in enumerate(all_services):
        inst_name = draw(_resource_name_st)
        # Ensure unique names by appending index
        inst_name = f"{inst_name}{i}"
        config = _minimal_config_for(svc)
        instance = ResourceInstanceIR(
            name=inst_name,
            service_type=svc,
            config=config,
        )
        modules.append(ServiceModuleIR(service_type=svc, instances=[instance]))
        all_module_refs.append(svc)

    project_name = draw(st.from_regex(r"[a-z][a-z0-9\-]{2,14}", fullmatch=True))

    return ProjectIR(
        project_name=project_name,
        environments=[
            EnvironmentIR(name="dev", variables={}, module_refs=all_module_refs),
        ],
        modules=modules,
        connections=[],
    )


@given(project=_mixed_project_ir())
@settings(max_examples=100)
def test_property_5_pipeline_skip_behavior_for_mixed_service_types(project):
    """Property 5: FileTreeAssembler produces module files only for full-generator
    resources and no files for icon-only resources, without raising errors.
    """
    assembler = FileTreeAssembler()
    file_tree = assembler.assemble(project)

    for module in project.modules:
        stype_name = module.service_type.value
        category = get_category(module.service_type)
        module_prefix = f"{project.project_name}/modules/{category}/{stype_name}/"

        module_files = [p for p in file_tree if p.startswith(module_prefix)]

        if module.service_type in GENERATOR_REGISTRY:
            # Full-generator service: should have module files
            assert len(module_files) > 0, (
                f"Expected module files for full-generator service {stype_name}, "
                f"but found none in file tree."
            )
        else:
            # Icon-only service: should have NO module files
            assert len(module_files) == 0, (
                f"Expected NO module files for icon-only service {stype_name}, "
                f"but found: {module_files}"
            )
