"""End-to-end checks that a generated project is real, loadable Terraform."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from app.models.ir_models import FileTree
from tests.hcl_assertions import (
    assert_no_path_collisions,
    assert_no_quoted_references,
    assert_tree_parses,
)
from tests.reference_project import (
    ENVIRONMENTS,
    PROJECT_NAME,
    colliding_route_connection_files,
    reference_connection_files,
    reference_tree,
)

needs_terraform = pytest.mark.skipif(
    shutil.which("terraform") is None, reason="terraform binary not installed"
)


def _write_tree(root: Path, tree: FileTree) -> None:
    for rel_path, content in tree.items():
        target = root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)


def _run_terraform(args: list[str], cwd: Path) -> None:
    result = subprocess.run(
        ["terraform", *args], cwd=cwd, capture_output=True, text=True, timeout=300
    )
    assert result.returncode == 0, (
        f"terraform {' '.join(args)} failed in {cwd}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_connection_files_do_not_collide() -> None:
    assert_no_path_collisions(reference_connection_files())


def test_distinct_route_paths_do_not_collide() -> None:
    assert_no_path_collisions(colliding_route_connection_files())


def test_generated_tree_is_syntactically_valid_hcl() -> None:
    assert_tree_parses(reference_tree())


def test_generated_tree_has_no_quoted_references() -> None:
    assert_no_quoted_references(reference_tree())


@pytest.mark.terraform
@needs_terraform
@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_generated_project_passes_terraform_validate(
    tmp_path: Path, environment: str
) -> None:
    _write_tree(tmp_path, reference_tree())
    env_dir = tmp_path / PROJECT_NAME / "environments" / environment
    assert env_dir.is_dir(), f"expected generated environment at {env_dir}"

    _run_terraform(["init", "-backend=false", "-input=false"], env_dir)
    _run_terraform(["validate"], env_dir)
