"""Several connections converging on one module must merge rather than collide."""

import pytest

from tests.hcl_assertions import assert_no_path_collisions
from tests.reference_project import reference_connection_files, reference_tree


@pytest.fixture(scope="module")
def tree():
    return reference_tree()


def _declarations(content: str, keyword: str) -> list[str]:
    return [
        line.split('"')[1]
        for line in content.splitlines()
        if line.startswith(f"{keyword} ")
    ]


class TestFanIn:
    """Two topics delivering to one queue."""

    def test_each_source_contributes_its_own_input(self, tree):
        variables = tree["reference-project/modules/messaging/sqs/jobs/variables.tf"]
        names = _declarations(variables, "variable")
        assert "events_topic_arn" in names
        assert "alerts_topic_arn" in names

    def test_each_source_gets_its_own_resources(self, tree):
        files = {p.rsplit("/", 1)[-1] for p in tree if "/sqs/jobs/" in p}
        assert {"subscription_events.tf", "subscription_alerts.tf"} <= files
        assert {"policy_events.tf", "policy_alerts.tf"} <= files

    def test_the_environment_passes_both(self, tree):
        main = tree["reference-project/environments/dev/main.tf"]
        block = main[main.index('module "jobs"') :]
        block = block[: block.index("}")]
        assert "events_topic_arn = module.events.arn" in block
        assert "alerts_topic_arn = module.alerts.arn" in block


class TestFanOut:
    """One topic delivering to two queues."""

    def test_each_target_receives_the_input(self, tree):
        for queue in ("jobs", "audit"):
            variables = tree[
                f"reference-project/modules/messaging/sqs/{queue}/variables.tf"
            ]
            assert "events_topic_arn" in _declarations(variables, "variable")

    def test_the_shared_output_is_declared_once(self, tree):
        outputs = tree["reference-project/modules/messaging/sns/events/outputs.tf"]
        names = _declarations(outputs, "output")
        assert names.count("arn") == 1


class TestNoCollisions:
    def test_converging_connections_never_share_a_path(self):
        assert_no_path_collisions(reference_connection_files())

    def test_a_module_never_declares_a_name_twice(self, tree):
        for path, content in tree.items():
            if not path.endswith((".tf",)):
                continue
            for keyword in ("variable", "output"):
                names = _declarations(content, keyword)
                assert len(names) == len(set(names)), f"duplicate {keyword} in {path}"
