"""FileTreeAssembler — walks ProjectIR and collects all generated content into a FileTree."""

from app.generators.global_config_generator import GlobalConfigGenerator
from app.generators.hcl_renderer import HCLRenderer
from app.generators.iam_policy_generator import IAMPolicyGenerator
from app.generators.registry import GENERATOR_REGISTRY
from app.generators.service_category_map import get_category
from app.generators.tfvars_generator import TfvarsGenerator
from app.models.input_models import ServiceType
from app.models.ir_models import (
    EnvironmentIR,
    FileTree,
    ProjectIR,
    ResourceInstanceIR,
    ServiceModuleIR,
    GeneratedFile,
)


class FileTreeAssembler:
    """Assembles the complete Terraform file tree from a ProjectIR and generated files."""

    def __init__(self) -> None:
        self._renderer = HCLRenderer()
        self._iam_policy_gen = IAMPolicyGenerator()
        self._tfvars_gen = TfvarsGenerator()
        self._global_config_gen = GlobalConfigGenerator()

    def assemble(
        self,
        project: ProjectIR,
        extra_files: list[GeneratedFile] | None = None,
    ) -> FileTree:
        """Build the full FileTree from the project IR.

        *extra_files* are additional files produced by the ConnectionProcessor
        (e.g. integration resources) that get merged into the tree.
        """
        tree: FileTree = {}
        root = project.project_name

        # Collect all resource instances across all modules
        all_instances: list[ResourceInstanceIR] = []
        for module in project.modules:
            all_instances.extend(module.instances)

        # 1. Environment files
        for env in project.environments:
            self._add_environment_files(tree, root, env, project, all_instances)

        # 2. Service module files + resource instance files
        for module in project.modules:
            self._add_service_module_files(tree, root, module)

        # 3. IAM policy JSON files
        self._add_iam_policy_files(tree, root, project)

        # 4. Merge extra files from connection processing
        if extra_files:
            for gf in extra_files:
                tree[gf.path] = gf.content

        return tree

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
    ) -> None:
        """Generate main.tf, variables.tf, outputs.tf, terraform.tfvars for an environment."""
        base = f"{root}/environments/{env.name}"

        # main.tf — provider + module blocks
        parts = [self._renderer.render_provider("aws", "var.aws_region")]
        for stype in env.module_refs:
            mod_name = stype.value
            source = f"../../modules/{mod_name}"
            parts.append(self._renderer.render_module(mod_name, source, {}))
        tree[f"{base}/main.tf"] = "\n".join(parts)

        # variables.tf — environment variables + resource terraform variables
        var_parts = [
            self._renderer.render_variable("aws_region", "string", "AWS region for this environment"),
        ]
        for key in sorted(env.variables.keys()):
            var_parts.append(self._renderer.render_variable(key, "string", f"Variable {key}"))
        resource_vars_tf = self._tfvars_gen.generate_variables_tf(all_instances)
        if resource_vars_tf:
            var_parts.append(resource_vars_tf)
        tree[f"{base}/variables.tf"] = "\n".join(var_parts)

        # outputs.tf
        out_parts = []
        for stype in env.module_refs:
            mod_name = stype.value
            out_parts.append(
                self._renderer.render_output(
                    f"{mod_name}_outputs",
                    f"module.{mod_name}",
                    f"Outputs from the {mod_name} module",
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
        tree[f"{base}/terraform.tfvars"] = "\n".join(tfvars_lines) + ("\n" if tfvars_lines else "")

        # Global config files: backend.tf, provider.tf, versions.tf
        global_cfg = project.global_config
        tree[f"{base}/backend.tf"] = self._global_config_gen.generate_backend_tf(global_cfg)
        tree[f"{base}/provider.tf"] = self._global_config_gen.generate_provider_tf(global_cfg)
        tree[f"{base}/versions.tf"] = self._global_config_gen.generate_versions_tf(global_cfg)

    # ------------------------------------------------------------------
    # Service module root files
    # ------------------------------------------------------------------

    def _add_service_module_files(
        self, tree: FileTree, root: str, module: ServiceModuleIR
    ) -> None:
        """Generate module-level main.tf, variables.tf, outputs.tf and per-instance files."""
        if module.service_type not in GENERATOR_REGISTRY:
            return
        stype_name = module.service_type.value
        mod_base = f"{root}/modules/{get_category(module.service_type)}/{stype_name}"

        # Separate layer instances from regular instances
        regular_instances = [i for i in module.instances if not i.config.is_layer]
        layer_instances = [i for i in module.instances if i.config.is_layer]

        # Module root main.tf — one module block per regular instance
        main_parts = []
        for inst in regular_instances:
            source = f"./{inst.name}"
            main_parts.append(self._renderer.render_module(inst.name, source, {}))
        tree[f"{mod_base}/main.tf"] = "\n".join(main_parts)

        # Module root variables.tf
        var_parts = []
        for inst in regular_instances:
            generator = GENERATOR_REGISTRY.get(module.service_type)
            if generator:
                # Collect variable names from the instance generator
                var_parts.append(
                    self._renderer.render_variable(
                        f"{inst.name}_config",
                        "any",
                        f"Configuration for {inst.name}",
                    )
                )
        tree[f"{mod_base}/variables.tf"] = "\n".join(var_parts)

        # Module root outputs.tf — aggregate outputs from regular instances
        out_parts = []
        for inst in regular_instances:
            out_parts.append(
                self._renderer.render_output(
                    f"{inst.name}_outputs",
                    f"module.{inst.name}",
                    f"Outputs from {inst.name}",
                )
            )
        tree[f"{mod_base}/outputs.tf"] = "\n".join(out_parts)

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
        """Generate a single layer.tf aggregating all layer instance definitions.

        Full implementation in task 2.2.
        """
        pass

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

        # Lambda gets an extra iam.tf
        if instance.service_type == ServiceType.LAMBDA:
            from app.generators.lambda_generator import LambdaGenerator

            if isinstance(generator, LambdaGenerator):
                tree[f"{inst_base}/iam.tf"] = generator.generate_iam_tf(instance)

    # ------------------------------------------------------------------
    # IAM policy JSON files
    # ------------------------------------------------------------------

    def _add_iam_policy_files(
        self, tree: FileTree, root: str, project: ProjectIR
    ) -> None:
        """Generate {name}-policy.json in iam-policies/ for every Lambda instance."""
        for module in project.modules:
            if module.service_type != ServiceType.LAMBDA:
                continue
            for inst in module.instances:
                policy_path = f"{root}/iam-policies/{inst.name}-policy.json"
                tree[policy_path] = self._iam_policy_gen.generate_policy_document(inst)
