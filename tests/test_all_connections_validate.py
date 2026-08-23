"""Every registered connection must generate Terraform that actually loads.

Derived from the registry, so a newly registered connection is covered without
anyone remembering to add a test for it.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.models.input_models import ArchitectureDescription
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import CONNECTION_SPECS
from app.services.ir_builder import IRBuilder
from tests.generator_helpers import connection_architecture
from tests.test_generated_project_validates import (
    _init_args,
    _terraform_env,
    _write_tree,
    needs_terraform,
)


def _spec_id(spec) -> str:
    return f"{spec.source.value}-{spec.target.value}-{spec.connection_type}"


@needs_terraform
@pytest.mark.parametrize("spec", CONNECTION_SPECS, ids=_spec_id)
def test_connection_generates_loadable_terraform(spec, tmp_path: Path) -> None:
    architecture = ArchitectureDescription.model_validate(connection_architecture(spec))
    tree = CodeGenerator().generate(IRBuilder().build(architecture))
    _write_tree(tmp_path, tree)

    env_dir = tmp_path / "connection-check/environments/dev"
    use_cache_dir = "-plugin-dir" not in " ".join(_init_args())
    environment = _terraform_env(use_cache_dir)

    init = subprocess.run(
        ["terraform", *_init_args(), "-no-color"],
        cwd=env_dir,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert init.returncode == 0, init.stderr

    result = subprocess.run(
        ["terraform", "validate", "-no-color"],
        cwd=env_dir,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert result.returncode == 0, result.stdout or result.stderr
