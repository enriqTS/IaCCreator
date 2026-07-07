"""HCL Renderer — produces syntactically valid HCL blocks with two-space indentation."""

from typing import Any


class HCLRenderer:
    """Low-level renderer for individual HCL block types.

    All output uses two-space indentation, no tabs.
    """

    INDENT = "  "

    # --- public API ---

    def render_resource(self, block_type: str, name: str, attrs: dict[str, Any]) -> str:
        """Render a Terraform ``resource`` block.

        Example::

            resource "aws_lambda_function" "my_func" {
              function_name = "my_func"
            }
        """
        lines = [f'resource "{block_type}" "{name}" {{']
        lines.extend(self._render_attrs(attrs, depth=1))
        lines.append("}")
        return "\n".join(lines) + "\n"

    def render_variable(
        self,
        name: str,
        var_type: str,
        description: str,
        default: Any | None = None,
    ) -> str:
        """Render a Terraform ``variable`` block with *type* and *description*."""
        lines = [f'variable "{name}" {{']
        lines.append(f"{self.INDENT}description = {self._quote(description)}")
        lines.append(f"{self.INDENT}type        = {var_type}")
        if default is not None:
            lines.append(f"{self.INDENT}default     = {self._format_value(default)}")
        lines.append("}")
        return "\n".join(lines) + "\n"

    def render_output(self, name: str, value: str, description: str) -> str:
        """Render a Terraform ``output`` block with *value* and *description*."""
        lines = [f'output "{name}" {{']
        lines.append(f"{self.INDENT}description = {self._quote(description)}")
        lines.append(f"{self.INDENT}value       = {value}")
        lines.append("}")
        return "\n".join(lines) + "\n"

    def render_module(self, name: str, source: str, variables: dict[str, str]) -> str:
        """Render a Terraform ``module`` block with *source* and variable assignments."""
        lines = [f'module "{name}" {{']
        lines.append(f"{self.INDENT}source = {self._quote(source)}")
        for var_name, var_value in variables.items():
            lines.append(f"{self.INDENT}{var_name} = {var_value}")
        lines.append("}")
        return "\n".join(lines) + "\n"

    def render_provider(self, provider: str, region: str) -> str:
        """Render a Terraform ``provider`` block with a configurable *region*."""
        lines = [f'provider "{provider}" {{']
        lines.append(f"{self.INDENT}region = {self._quote(region)}")
        lines.append("}")
        return "\n".join(lines) + "\n"

    # --- private helpers ---

    def _render_attrs(self, attrs: dict[str, Any], depth: int) -> list[str]:
        """Recursively render attribute key-value pairs at the given indentation *depth*."""
        indent = self.INDENT * depth
        lines: list[str] = []
        for key, value in attrs.items():
            if isinstance(value, dict):
                # Nested block
                lines.append(f"{indent}{key} {{")
                lines.extend(self._render_attrs(value, depth + 1))
                lines.append(f"{indent}}}")
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                # Repeated nested blocks (e.g., multiple ``attribute`` blocks)
                for item in value:
                    lines.append(f"{indent}{key} {{")
                    lines.extend(self._render_attrs(item, depth + 1))
                    lines.append(f"{indent}}}")
            else:
                lines.append(f"{indent}{key} = {self._format_value(value)}")
        return lines

    @staticmethod
    def _format_value(value: Any) -> str:
        """Format a Python value as an HCL literal."""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            # Terraform references / expressions are passed through unquoted
            if value.startswith(("var.", "module.", "aws_", "local.", "data.")):
                return value
            return f'"{value}"'
        if isinstance(value, list):
            items = ", ".join(HCLRenderer._format_value(v) for v in value)
            return f"[{items}]"
        return f'"{value}"'

    @staticmethod
    def _quote(s: str) -> str:
        """Wrap a string in double quotes, escaping inner quotes."""
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
