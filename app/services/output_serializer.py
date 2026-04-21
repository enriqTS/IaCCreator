"""OutputSerializer — converts a FileTree into ZIP archive or JSON response."""

import io
import zipfile

from app.models.ir_models import FileTree, GenerationSummary


class OutputSerializer:
    """Serializes a FileTree into downloadable formats."""

    def to_zip(self, file_tree: FileTree, strip_prefix: str | None = None) -> bytes:
        """Produce a valid ZIP archive from the file tree.

        Each key in *file_tree* becomes a file path inside the archive,
        and the corresponding value becomes the file content (UTF-8 encoded).

        If *strip_prefix* is given, that prefix (plus a trailing ``/``) is
        removed from every path so the ZIP contents sit at the root level.
        """
        prefix = f"{strip_prefix}/" if strip_prefix else ""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(file_tree):
                archive_path = path.removeprefix(prefix) if prefix else path
                zf.writestr(archive_path, file_tree[path])
        return buf.getvalue()

    def to_json(self, file_tree: FileTree, summary: GenerationSummary) -> dict:
        """Produce a JSON-serializable dict with ``files`` and ``summary`` keys."""
        return {
            "files": file_tree,
            "summary": summary.model_dump(),
        }
