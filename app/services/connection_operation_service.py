"""Backend application of schema-defined linked connection edits."""

from copy import deepcopy

from app.models.connection_operations import LinkedEntryOperation
from app.models.diagram_models import DiagramStateInput
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec


class ConnectionOperationService:
    """Materialize linked-entry intent using connection registry metadata."""

    def apply(
        self, diagram: DiagramStateInput, operation: LinkedEntryOperation
    ) -> DiagramStateInput:
        state = deepcopy(diagram.model_dump())
        objects = {obj["id"]: obj for obj in state["canvasObjects"]}
        connectors = {item["id"]: item for item in state["connectors"]}
        connector_id = operation.connector_id
        if operation.operation == "remove" and connector_id is None:
            connector_id = self._find_linked_connector(
                objects,
                connectors,
                operation.source_block_id,
                operation.field_key,
                operation.display_value,
            )
        connector = connectors.get(connector_id)
        if connector is None:
            raise ValueError(f"Unknown connector: {operation.connector_id}")
        source = objects.get(connector["sourceId"])
        target = objects.get(connector["targetId"])
        if source is None or target is None:
            raise ValueError("Connector endpoints are missing")
        config = (
            connector.get("connection_config")
            or connector.get("connectionConfig")
            or {}
        )
        spec = resolve_spec(
            ServiceType(source.get("serviceType")),
            ServiceType(target.get("serviceType")),
            connector["connectionType"],
            config,
        )
        if spec is None:
            raise ValueError("Connection is not supported")
        field = next(
            (
                entry
                for entry in spec.config_model.get_field_schema()
                if entry.key == operation.field_key
            ),
            None,
        )
        if field is None or field.linked is None:
            raise ValueError(f"Connection field is not linked: {operation.field_key}")
        linked = field.linked
        source_config = source.setdefault("config", {})
        entries = list(self._get_path(source_config, linked.config_path) or [])

        if operation.operation == "create":
            if any(
                entry.get(linked.display_key) == operation.display_value
                for entry in entries
            ):
                raise ValueError("Linked entry already exists")
            allowed = {entry.key for entry in linked.entry_fields}
            if not set(operation.entry_values).issubset(allowed):
                raise ValueError("Linked entry contains unsupported fields")
            entry = dict(linked.create_template)
            entry[linked.display_key] = operation.display_value
            if linked.target_name_key:
                entry[linked.target_name_key] = target.get("name", "")
            if linked.target_id_key:
                entry[linked.target_id_key] = target["id"]
            for entry_field in linked.entry_fields:
                if entry_field.default is not None:
                    entry.setdefault(entry_field.key, entry_field.default)
            entry.update(operation.entry_values)
            entries.append(entry)
            connector["connection_config"] = {
                **config,
                field.key: operation.display_value,
            }
        elif operation.operation == "update":
            if not any(
                entry.get(linked.display_key) == operation.display_value
                for entry in entries
            ):
                raise ValueError("Linked entry does not exist")
            allowed = {entry.key for entry in linked.entry_fields}
            if operation.entry_field_key not in allowed:
                raise ValueError("Linked entry field is not editable")
            entries = [
                {**entry, operation.entry_field_key: operation.entry_field_value}
                if entry.get(linked.display_key) == operation.display_value
                else entry
                for entry in entries
            ]
        else:
            if not any(
                entry.get(linked.display_key) == operation.display_value
                for entry in entries
            ):
                raise ValueError("Linked entry does not exist")
            entries = [
                entry
                for entry in entries
                if entry.get(linked.display_key) != operation.display_value
            ]
            updated_config = dict(config)
            if updated_config.get(field.key) == operation.display_value:
                updated_config.pop(field.key)
            connector["connection_config"] = updated_config

        self._set_path(source_config, linked.config_path, entries)
        connector.pop("connectionConfig", None)
        return DiagramStateInput.model_validate(state)

    @staticmethod
    def _find_linked_connector(
        objects: dict,
        connectors: dict,
        source_id: str | None,
        field_key: str,
        display_value: str,
    ) -> str | None:
        """Resolve a linked entry to its connector using registry metadata."""
        source = objects.get(source_id)
        if source is None:
            return None
        for connector in connectors.values():
            if connector["sourceId"] != source_id:
                continue
            target = objects.get(connector["targetId"])
            if target is None:
                continue
            config = connector.get("connection_config") or {}
            spec = resolve_spec(
                ServiceType(source.get("serviceType")),
                ServiceType(target.get("serviceType")),
                connector["connectionType"],
                config,
            )
            if spec is None:
                continue
            field = next(
                (
                    entry
                    for entry in spec.config_model.get_field_schema()
                    if entry.key == field_key and entry.linked is not None
                ),
                None,
            )
            if field is None or field.linked is None:
                continue
            entries = (
                ConnectionOperationService._get_path(
                    source.get("config") or {}, field.linked.config_path
                )
                or []
            )
            for entry in entries:
                if entry.get(field.linked.display_key) != display_value:
                    continue
                if field.linked.target_id_key and entry.get(
                    field.linked.target_id_key
                ) == target.get("id"):
                    return connector["id"]
                if field.linked.target_name_key and entry.get(
                    field.linked.target_name_key
                ) == target.get("name"):
                    return connector["id"]
        return None

    @staticmethod
    def _get_path(config: dict, path: str):
        """Read a dot-separated path from nested configuration."""
        value = config
        for part in path.split("."):
            if not isinstance(value, dict):
                return None
            value = value.get(part)
        return value

    @staticmethod
    def _set_path(config: dict, path: str, value) -> None:
        """Write a dot-separated path into nested configuration."""
        target = config
        parts = path.split(".")
        for part in parts[:-1]:
            child = target.get(part)
            if not isinstance(child, dict):
                child = {}
                target[part] = child
            target = child
        target[parts[-1]] = value
