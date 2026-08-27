"""Stored diagrams are upgraded on read so the API only ever serves the current format."""

from app.models.diagram_state import CURRENT_DIAGRAM_VERSION
from app.persistence.models import DiagramRecord
from app.services.diagram_migrations import migrate_diagram_state

V1 = {
    "version": 1,
    "projectName": "legacy",
    "environments": [],
    "connectors": [],
    "elements": [
        {
            "id": "el-1",
            "serviceType": "lambda",
            "name": "worker",
            "position": {"x": 10, "y": 20},
            "config": {"function_name": "worker"},
        }
    ],
}


class TestVersionOneUpgrade:
    def test_elements_become_canvas_objects(self):
        state = migrate_diagram_state(V1)
        assert "elements" not in state
        assert [o["objectType"] for o in state["canvasObjects"]] == [
            "architecture-block"
        ]

    def test_position_and_config_are_preserved(self):
        obj = migrate_diagram_state(V1)["canvasObjects"][0]
        assert (obj["x"], obj["y"]) == (10, 20)
        assert obj["config"] == {"function_name": "worker"}

    def test_default_visuals_are_applied(self):
        obj = migrate_diagram_state(V1)["canvasObjects"][0]
        assert obj["visualConfig"] == {"width": 80.0, "height": 80.0}

    def test_terraform_variables_are_seeded_from_the_schema(self):
        obj = migrate_diagram_state(V1)["canvasObjects"][0]
        assert obj["terraformVariables"]["runtime"] == "python3.14"

    def test_z_index_follows_declaration_order(self):
        state = migrate_diagram_state({**V1, "elements": V1["elements"] * 3})
        assert [o["zIndex"] for o in state["canvasObjects"]] == [0, 1, 2]


class TestVersionTwoUpgrade:
    def _line(self, **overrides):
        line = {"id": "l-1", "objectType": "line", "name": "", **overrides}
        return {"version": 2, "canvasObjects": [line]}

    def test_anchored_line_gains_default_positions(self):
        state = migrate_diagram_state(
            self._line(sourceAnchorObjectId="a", targetAnchorObjectId="b")
        )
        line = state["canvasObjects"][0]
        assert line["sourceAnchorPosition"] == "right"
        assert line["targetAnchorPosition"] == "left"

    def test_existing_positions_are_left_alone(self):
        state = migrate_diagram_state(
            self._line(sourceAnchorObjectId="a", sourceAnchorPosition="top")
        )
        assert state["canvasObjects"][0]["sourceAnchorPosition"] == "top"

    def test_unanchored_line_gets_explicit_nulls(self):
        line = migrate_diagram_state(self._line())["canvasObjects"][0]
        assert line["sourceAnchorObjectId"] is None
        assert line["targetAnchorObjectId"] is None


class TestVersionThreeUpgrade:
    def test_semantic_and_connector_defaults_are_explicit(self):
        state = migrate_diagram_state(
            {
                "version": 3,
                "canvasObjects": [
                    {
                        "id": "vpc",
                        "objectType": "architecture-block",
                        "serviceType": "vpc",
                        "name": "vpc",
                    }
                ],
                "connectors": [
                    {
                        "id": "connection",
                        "sourceId": "vpc",
                        "targetId": "vpc",
                        "connectionType": "legacy",
                    }
                ],
            }
        )
        assert state["canvasObjects"][0]["parentContainerId"] is None
        assert state["canvasObjects"][0]["presentation"] == "node"
        assert state["connectors"][0]["origin"] == "explicit"
        assert state["connectors"][0]["container_id"] is None


class TestNormalisation:
    def test_unknown_shape_falls_back_to_rectangle(self):
        state = migrate_diagram_state(
            {
                "version": 3,
                "canvasObjects": [
                    {
                        "id": "g",
                        "objectType": "geometric",
                        "name": "",
                        "visualConfig": {"shape": "not-a-shape"},
                    }
                ],
            }
        )
        assert state["canvasObjects"][0]["visualConfig"]["shape"] == "rectangle"

    def test_unknown_uml_kind_falls_back_to_class(self):
        state = migrate_diagram_state(
            {
                "version": 3,
                "canvasObjects": [
                    {"id": "u", "objectType": "uml", "name": "", "umlKind": "nonsense"}
                ],
            }
        )
        assert state["canvasObjects"][0]["umlKind"] == "class"

    def test_missing_visuals_are_filled_in(self):
        state = migrate_diagram_state(
            {
                "version": 3,
                "canvasObjects": [{"id": "t", "objectType": "text", "name": ""}],
            }
        )
        assert state["canvasObjects"][0]["visualConfig"]["fontSize"] == 14.0

    def test_current_version_is_always_stamped(self):
        assert migrate_diagram_state({})["version"] == CURRENT_DIAGRAM_VERSION


class TestMigrationHappensOnRead:
    def test_records_are_upgraded_when_loaded(self):
        record = DiagramRecord(
            diagram_id="d",
            session_id="s",
            project_name="legacy",
            diagram_state=dict(V1),
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        assert record.diagram_state["version"] == CURRENT_DIAGRAM_VERSION
        assert "elements" not in record.diagram_state
