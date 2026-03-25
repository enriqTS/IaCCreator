"""CodeGenerator — orchestrates the full generation pipeline from ProjectIR to FileTree."""

from app.models.ir_models import FileTree, ProjectIR
from app.services.connection_processor import ConnectionProcessor
from app.services.file_tree_assembler import FileTreeAssembler


class CodeGenerator:
    """Top-level orchestrator: connections → file tree assembly.

    Pipeline:
    1. Process connections (produces integration files + mutates IAM statements)
    2. Assemble the complete file tree from the enriched ProjectIR
    """

    def __init__(self) -> None:
        self._connection_processor = ConnectionProcessor()
        self._assembler = FileTreeAssembler()

    def generate(self, project: ProjectIR) -> FileTree:
        """Generate the complete Terraform file tree for a project.

        The ConnectionProcessor is run first so that IAM statements are
        attached to Lambda instances before the assembler generates
        iam.tf and policy JSON files.
        """
        # 1. Process connections — produces extra files and enriches IAM statements
        extra_files = self._connection_processor.process_all(project)

        # 2. Assemble the full file tree
        return self._assembler.assemble(project, extra_files=extra_files)
