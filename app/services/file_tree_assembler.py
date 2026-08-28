"""FileTreeAssembler — walks ProjectIR and collects all generated content into a FileTree."""

from app.generators.execution_role_generator import ExecutionRoleGenerator
from app.generators.global_config_generator import GlobalConfigGenerator
from app.generators.hcl_renderer import HCLRenderer
from app.generators.iam_policy_generator import IAMPolicyGenerator
from app.generators.module_arguments import module_arguments
from app.generators.module_paths import instance_module_dir
from app.generators.registry import GENERATOR_REGISTRY
from app.generators.service_category_map import get_category
from app.generators.tfvars_generator import TfvarsGenerator
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    EnvironmentIR,
    FileTree,
    ProjectIR,
    ResourceInstanceIR,
    ServiceModuleIR,
)


class FileTreeAssembler:
    """Assembles the complete Terraform file tree from a ProjectIR and generated files."""

    def __init__(self) -> None:
        self._renderer = HCLRenderer()
        self._iam_policy_gen = IAMPolicyGenerator()
        self._tfvars_gen = TfvarsGenerator()
        self._global_config_gen = GlobalConfigGenerator()
        self._role_gen = ExecutionRoleGenerator()

    def assemble(
        self,
        project: ProjectIR,
        contribution: ConnectionContribution | None = None,
    ) -> FileTree:
        """Build the full FileTree, folding in whatever the connections contributed."""
        contribution = contribution or ConnectionContribution()
        tree: FileTree = {}
        root = project.project_name

        # Collect all resource instances across all modules
        all_instances: list[ResourceInstanceIR] = []
        for module in project.modules:
            all_instances.extend(module.instances)

        instances = {inst.name: inst for inst in all_instances}

        # 1. Environment files
        for env in project.environments:
            self._add_environment_files(
                tree, root, env, project, all_instances, contribution
            )

        # 2. Service module files + resource instance files
        for module in project.modules:
            self._add_service_module_files(tree, root, module)

        # 3. IAM policy JSON files
        self._add_iam_policy_files(tree, root, project)

        # 4. Connection resources live inside the module that owns them
        for resource in contribution.resources:
            instance = instances.get(resource.module)
            if instance is None:
                continue
            tree[f"{instance_module_dir(root, instance)}/{resource.filename}"] = (
                resource.content
            )

        # 5. Connection inputs and outputs extend the module's own variables and outputs
        self._add_connection_variables(tree, root, contribution, instances)
        self._add_connection_outputs(tree, root, contribution, instances)

        return tree

    # ------------------------------------------------------------------
    # Connection wiring
    # ------------------------------------------------------------------

    def _add_connection_variables(
        self,
        tree: FileTree,
        root: str,
        contribution: ConnectionContribution,
        instances: dict[str, ResourceInstanceIR],
    ) -> None:
        """Append a variable block per connection input to the receiving module."""
        for module_input in contribution.inputs:
            instance = instances.get(module_input.module)
            if instance is None:
                continue
            path = f"{instance_module_dir(root, instance)}/variables.tf"
            existing = tree.get(path, "")
            if f'variable "{module_input.name}"' in existing:
                continue
            block = self._renderer.render_variable(
                module_input.name, module_input.type, module_input.description
            )
            tree[path] = (existing.rstrip("\n") + "\n\n" + block).lstrip("\n")

    def _add_connection_outputs(
        self,
        tree: FileTree,
        root: str,
        contribution: ConnectionContribution,
        instances: dict[str, ResourceInstanceIR],
    ) -> None:
        """Append an output block per connection output to the providing module."""
        for module_output in contribution.outputs:
            instance = instances.get(module_output.module)
            if instance is None:
                continue
            path = f"{instance_module_dir(root, instance)}/outputs.tf"
            existing = tree.get(path, "")
            if f'output "{module_output.name}"' in existing:
                continue
            block = self._renderer.render_output(
                module_output.name, module_output.value, module_output.description
            )
            tree[path] = (existing.rstrip("\n") + "\n\n" + block).lstrip("\n")

    # ------------------------------------------------------------------
    # Environment files
    # ------------------------------------------------------------------

    def _add_environment_files(
        self,
        tree: FileTree,
        root: str,
        env: EnvironmentIR,
        project: ProjectIR,
        all_instances: list[ResourceInstanceIR],
        contribution: ConnectionContribution,
    ) -> None:
        """Generate main.tf, variables.tf, outputs.tf, terraform.tfvars for an environment."""
        base = f"{root}/environments/{env.name}"

        # provider.tf owns the provider block, so main.tf carries only module wiring
        default_region = env.variables.get(
            "region", project.global_config.provider_region
        )
        parts: list[str] = []
        for inst in all_instances:
            if inst.service_type not in GENERATOR_REGISTRY or inst.config.is_layer:
                continue
            parts.append(
                self._renderer.render_module(
                    inst.name,
                    self._module_source(inst),
                    self._environment_module_arguments(
                        inst,
                        contribution,
                        default_region,
                        "region" in env.variables,
                    ),
                )
            )
        tree[f"{base}/main.tf"] = "\n".join(parts)

        # variables.tf — environment variables + resource terraform variables
        var_parts = [
            self._renderer.render_variable(
                "aws_region", "string", "AWS region for this environment"
            ),
        ]
        for key in sorted(env.variables.keys()):
            var_parts.append(
                self._renderer.render_variable(key, "string", f"Variable {key}")
            )
        resource_vars_tf = self._tfvars_gen.generate_variables_tf(all_instances)
        if resource_vars_tf:
            var_parts.append(resource_vars_tf)
        tree[f"{base}/variables.tf"] = "\n".join(var_parts)

        # outputs.tf
        out_parts = []
        for inst in all_instances:
            if inst.service_type not in GENERATOR_REGISTRY or inst.config.is_layer:
                continue
            out_parts.append(
                self._renderer.render_output(
                    f"{self._safe_name(inst.name)}_outputs",
                    f"module.{inst.name}",
                    f"Outputs from {inst.name}",
                )
            )
        tree[f"{base}/outputs.tf"] = "\n".join(out_parts) if out_parts else ""

        # terraform.tfvars — environment variables + resource terraform variables
        tfvars_lines = []
        for key in sorted(env.variables.keys()):
            val = env.variables[key]
            tfvars_lines.append(f'{key} = "{val}"')
        resource_tfvars = self._tfvars_gen.generate_tfvars(all_instances)
        if resource_tfvars:
            tfvars_lines.append(resource_tfvars.rstrip("\n"))
        tree[f"{base}/terraform.tfvars"] = "\n".join(tfvars_lines) + (
            "\n" if tfvars_lines else ""
        )

        # Global config files: backend.tf, provider.tf, versions.tf
        global_cfg = project.global_config
        tree[f"{base}/backend.tf"] = self._global_config_gen.generate_backend_tf(
            global_cfg
        )
        regions = {
            env.variables.get("region", inst.provider_region or default_region)
            for inst in all_instances
            if inst.service_type in GENERATOR_REGISTRY and not inst.config.is_layer
        }
        tree[f"{base}/provider.tf"] = self._global_config_gen.generate_provider_tf(
            global_cfg, default_region, regions
        )
        tree[f"{base}/versions.tf"] = self._global_config_gen.generate_versions_tf(
            global_cfg
        )

    # ------------------------------------------------------------------
    # Module wiring helpers
    # ------------------------------------------------------------------

    def _environment_module_arguments(
        self,
        instance: ResourceInstanceIR,
        contribution: ConnectionContribution,
        default_region: str,
        environment_overrides_region: bool,
    ) -> dict[str, str]:
        arguments = self._module_arguments(instance, contribution)
        region = (
            default_region
            if environment_overrides_region
            else instance.provider_region or default_region
        )
        if region != default_region:
            alias = self._global_config_gen.provider_alias(region)
            return {"providers": f"{{ aws = aws.{alias} }}", **arguments}
        return arguments

    @staticmethod
    def _safe_name(name: str) -> str:
        """Convert a resource name into a Terraform identifier safe to reference."""
        return name.replace("-", "_")

    @staticmethod
    def _module_source(instance: ResourceInstanceIR) -> str:
        """Path from an environment directory to an instance module."""
        category = get_category(instance.service_type)
        return f"../../modules/{category}/{instance.service_type.value}/{instance.name}"

    def _module_arguments(
        self, instance: ResourceInstanceIR, contribution: ConnectionContribution
    ) -> dict[str, str]:
        """Render the argument assignments an instance module requires."""
        generator = GENERATOR_REGISTRY.get(instance.service_type)
        if generator is None:
            return {}
        variables_tf = generator.generate_variables_tf(instance)
        arguments = {
            name: self._renderer._format_expression(value, depth=1)
            for name, value in module_arguments(instance, variables_tf).items()
        }
        for module_input in contribution.inputs:
            if module_input.module == instance.name:
                arguments[module_input.name] = module_input.value
        return arguments

    # ------------------------------------------------------------------
    # Service module files
    # ------------------------------------------------------------------

    def _add_service_module_files(
        self, tree: FileTree, root: str, module: ServiceModuleIR
    ) -> None:
        """Generate the per-instance module files for one service type."""
        if module.service_type not in GENERATOR_REGISTRY:
            return
        stype_name = module.service_type.value
        mod_base = f"{root}/modules/{get_category(module.service_type)}/{stype_name}"

        # Separate layer instances from regular instances
        regular_instances = [i for i in module.instances if not i.config.is_layer]
        layer_instances = [i for i in module.instances if i.config.is_layer]

        # Per-instance subfolders (regular instances only)
        for inst in regular_instances:
            self._add_resource_instance_files(tree, mod_base, inst)

        # Lambda layer aggregation (handled in task 2.2)
        if layer_instances:
            self._add_layer_file(tree, mod_base, layer_instances)

    # ------------------------------------------------------------------
    # Lambda layer aggregation
    # ------------------------------------------------------------------

    def _add_layer_file(
        self, tree: FileTree, mod_base: str, layer_instances: list[ResourceInstanceIR]
    ) -> None:
        """Generate a single layer.tf aggregating all layer instance definitions."""
        from app.generators.lambda_generator import LambdaGenerator

        generator = GENERATOR_REGISTRY.get(ServiceType.LAMBDA)
        if not isinstance(generator, LambdaGenerator):
            return

        parts: list[str] = []
        for inst in layer_instances:
            resource_tf = generator.generate_resource_tf(inst)
            variables_tf = generator.generate_variables_tf(inst)
            outputs_tf = generator.generate_outputs_tf(inst)
            parts.append(resource_tf)
            parts.append(variables_tf)
            parts.append(outputs_tf)

        tree[f"{mod_base}/layer.tf"] = "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Resource instance files
    # ------------------------------------------------------------------

    def _add_resource_instance_files(
        self, tree: FileTree, mod_base: str, instance: ResourceInstanceIR
    ) -> None:
        """Generate {service_type}.tf, variables.tf, outputs.tf (and iam.tf for Lambda)."""
        inst_base = f"{mod_base}/{instance.name}"
        stype_name = instance.service_type.value

        generator = GENERATOR_REGISTRY.get(instance.service_type)
        if generator is None:
            return

        # Main resource file named after service type
        tree[f"{inst_base}/{stype_name}.tf"] = generator.generate_resource_tf(instance)
        tree[f"{inst_base}/variables.tf"] = generator.generate_variables_tf(instance)
        tree[f"{inst_base}/outputs.tf"] = generator.generate_outputs_tf(instance)

        # Any service that assumes a role carries its own role and policy
        if type(instance.config).owns_execution_role:
            tree[f"{inst_base}/iam.tf"] = self._role_gen.generate_iam_tf(instance)

    # ------------------------------------------------------------------
    # IAM policy JSON files
    # ------------------------------------------------------------------

    def _add_iam_policy_files(
        self, tree: FileTree, root: str, project: ProjectIR
    ) -> None:
        """Generate {name}-policy.json for every instance that owns an execution role."""
        for module in project.modules:
            for inst in module.instances:
                if not type(inst.config).owns_execution_role:
                    continue
                policy_path = f"{root}/iam-policies/{inst.name}-policy.json"
                tree[policy_path] = self._iam_policy_gen.generate_policy_document(inst)
