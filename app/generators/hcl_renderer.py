"""HCL Renderer — produces syntactically valid HCL blocks with two-space indentation."""

import json
import re
from typing import Any

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


class Expr(str):
    """A raw HCL expression, emitted unquoted — anything else is a quoted literal."""


class HCLRenderer:
    """Low-level renderer for individual HCL block types."""

    INDENT = "  "

    # --- public API ---

    def render_resource(self, block_type: str, name: str, attrs: dict[str, Any]) -> str:
        """Render a Terraform ``resource`` block."""
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

    def render_json_policy(self, document: dict[str, Any], depth: int = 1) -> Expr:
        """Render a policy document as a ``jsonencode(...)`` expression."""
        body = self._format_expression(document, depth=depth)
        return Expr(f"jsonencode({body})")

    # --- private helpers ---

    def _render_attrs(self, attrs: dict[str, Any], depth: int) -> list[str]:
        """Recursively render attribute key-value pairs at the given indentation *depth*."""
        indent = self.INDENT * depth
        lines: list[str] = []
        for key, value in attrs.items():
            if isinstance(value, dict):
                # A bare dict is a nested block, not an object value
                lines.append(f"{indent}{key} {{")
                lines.extend(self._render_attrs(value, depth + 1))
                lines.append(f"{indent}}}")
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                # Repeated nested blocks (e.g. multiple ``attribute`` blocks)
                for item in value:
                    lines.append(f"{indent}{key} {{")
                    lines.extend(self._render_attrs(item, depth + 1))
                    lines.append(f"{indent}}}")
            else:
                lines.append(f"{indent}{key} = {self._format_value(value)}")
        return lines

    def _format_expression(self, value: Any, depth: int) -> str:
        """Render a value as an HCL expression, using object and tuple syntax for containers."""
        indent = self.INDENT * depth
        closing = self.INDENT * (depth - 1)

        if isinstance(value, Expr):
            return str(value)

        if isinstance(value, dict):
            if not value:
                return "{}"
            entries = [
                f"{indent}{self._format_key(k)} = {self._format_expression(v, depth + 1)}"
                for k, v in value.items()
            ]
            return "{\n" + "\n".join(entries) + f"\n{closing}}}"

        if isinstance(value, list):
            if not value:
                return "[]"
            items = [f"{indent}{self._format_expression(v, depth + 1)}" for v in value]
            return "[\n" + ",\n".join(items) + f"\n{closing}]"

        return self._format_value(value)

    @staticmethod
    def _format_key(key: Any) -> str:
        """Emit an object key bare when it is a valid HCL identifier, quoted otherwise."""
        text = str(key)
        return text if _IDENTIFIER.match(text) else json.dumps(text)

    @staticmethod
    def _format_value(value: Any) -> str:
        """Format a Python value as an HCL literal, passing Expr through unquoted."""
        if isinstance(value, Expr):
            return str(value)
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            return json.dumps(value)
        if isinstance(value, list):
            items = ", ".join(HCLRenderer._format_value(v) for v in value)
            return f"[{items}]"
        return json.dumps(str(value))

    @staticmethod
    def _quote(s: str) -> str:
        """Wrap a string in double quotes, escaping its contents."""
        return json.dumps(s)
