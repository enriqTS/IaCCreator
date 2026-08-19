"""Structural assertions for generated HCL and file trees."""

from __future__ import annotations

import io
from collections import Counter

import hcl2

from app.models.ir_models import FileTree, GeneratedFile


def parse_hcl(content: str) -> dict:
    """Parse HCL text, raising AssertionError with the offending source on failure."""
    try:
        return hcl2.load(io.StringIO(content))
    except Exception as exc:
        raise AssertionError(f"generated HCL does not parse: {exc}\n---\n{content}") from exc


def assert_parses(content: str) -> dict:
    """Assert that a rendered HCL block is syntactically valid."""
    return parse_hcl(content)


def assert_tree_parses(tree: FileTree) -> None:
    """Assert every .tf file in a generated tree is syntactically valid HCL."""
    failures: list[str] = []
    for path, content in sorted(tree.items()):
        if not path.endswith(".tf"):
            continue
        try:
            hcl2.load(io.StringIO(content))
        except Exception as exc:
            failures.append(f"{path}: {exc}")
    assert not failures, "invalid HCL in generated tree:\n" + "\n".join(failures)


def assert_no_path_collisions(files: list[GeneratedFile]) -> None:
    """Assert no two generated files claim the same path, since the tree silently overwrites."""
    counts = Counter(f.path for f in files)
    duplicates = sorted(path for path, count in counts.items() if count > 1)
    assert not duplicates, "generated files collide on paths: " + ", ".join(duplicates)
