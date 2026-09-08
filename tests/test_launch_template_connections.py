"""Managed launch templates complete Auto Scaling network placement."""

from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.exceptions import InvalidConnectionConfigError
from app.models.input_models import ArchitectureDescription, ServiceType
from app.models.input_models.ec2_launch_template_config import Ec2LaunchTemplateConfig
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from app.services.connection_processor import ConnectionProcessor
from app.services.ir_builder import IRBuilder
from app.services.service_catalog import SERVICE_CATALOG
from tests.generator_helpers import connection_architecture, minimal_config_for
from tests.hcl_assertions import assert_tree_parses


def launch_architecture():
    return connection_architecture(
        resolve_spec(
            ServiceType.EC2_LAUNCH_TEMPLATE,
            ServiceType.EC2_AUTO_SCALING,
            "launches",
            {},
        )
    )


def project(payload):
    return IRBuilder().build(ArchitectureDescription.model_validate(payload))


def test_managed_template_overrides_external_id_and_symbolic_version():
    payload = launch_architecture()
    payload["resources"][1]["config"].update(
        launch_template_id="lt-external", launch_template_version="$Default"
    )
    ir = project(payload)
    assert ConnectionPreviewer().preview_all(ir)[0].issues == []
    contribution = ConnectionProcessor().process_all(ir)
    assert not contribution.resources
    assert not contribution.iam
    assert {item.module for item in contribution.inputs} == {"target-resource"}
    tree = CodeGenerator().generate(ir)
    assert_tree_parses(tree)
    main = tree["connection-check/environments/dev/main.tf"]
    assert "launch_template_id = module.source-resource.launch_template_id" in main
    assert (
        "launch_template_version = tostring(module.source-resource.latest_version)"
        in main
    )
    template = next(
        content
        for path, content in tree.items()
        if path.endswith("/ec2-launch-template.tf")
    )
    assert "vpc_security_group_ids = var.security_group_ids" in template
    assert 'http_tokens = "required"' in template
    assert "subnet_id" not in template


@given(order=st.permutations([0, 1, 2]))
def test_shared_template_and_duplicate_connections_are_deterministic(order):
    payload = launch_architecture()
    group = deepcopy(payload["resources"][1])
    group.update(id="other", name="other-group")
    payload["resources"].append(group)
    payload["connections"].append(
        dict(payload["connections"][0], target="other-group", target_id="other")
    )
    payload["connections"].append(dict(payload["connections"][0]))
    baseline = CodeGenerator().generate(project(payload))
    payload["connections"] = [payload["connections"][index] for index in order]
    assert dict(CodeGenerator().generate(project(payload))) == dict(baseline)


def test_multiple_templates_for_one_group_are_rejected():
    payload = launch_architecture()
    template = deepcopy(payload["resources"][0])
    template.update(id="other", name="other-template")
    payload["resources"].append(template)
    payload["connections"].append(
        dict(payload["connections"][0], source="other-template", source_id="other")
    )
    with pytest.raises(
        InvalidConnectionConfigError, match="only one managed launch template"
    ):
        CodeGenerator().generate(project(payload))


def test_external_template_escape_hatch_remains_available():
    payload = launch_architecture()
    payload["connections"] = []
    payload["resources"][1]["config"].update(
        launch_template_id="lt-external", launch_template_version="7"
    )
    tree = CodeGenerator().generate(project(payload))
    assert (
        'launch_template_id = "lt-external"'
        in tree["connection-check/environments/dev/main.tf"]
    )
    assert (
        'launch_template_version = "7"'
        in tree["connection-check/environments/dev/main.tf"]
    )


def test_template_schema_catalog_and_invalid_connections():
    metadata = SERVICE_CATALOG[ServiceType.EC2_LAUNCH_TEMPLATE]
    assert (
        metadata.capabilities.diagram
        and metadata.capabilities.terraform
        and metadata.capabilities.connectable
    )
    assert metadata.category == "compute"
    fields = {
        field.name: field for field in Ec2LaunchTemplateConfig.get_variable_schema()
    }
    assert fields["image_id"].required
    assert fields["security_group_ids"].type == "list"
    spec = resolve_spec(
        ServiceType.EC2_LAUNCH_TEMPLATE, ServiceType.EC2_AUTO_SCALING, "launches", {}
    )
    with pytest.raises(ValidationError):
        spec.config_model.model_validate({"subnet_id": "subnet-invalid"})
    assert (
        resolve_spec(
            ServiceType.EC2_AUTO_SCALING,
            ServiceType.EC2_LAUNCH_TEMPLATE,
            "launches",
            {},
        )
        is None
    )
    assert (
        resolve_spec(ServiceType.SUBNET, ServiceType.EC2_LAUNCH_TEMPLATE, "places", {})
        is None
    )
    assert (
        resolve_spec(
            ServiceType.SECURITY_GROUP, ServiceType.EC2_AUTO_SCALING, "associates", {}
        )
        is None
    )


def networking_architecture():
    nodes = {
        "network": (ServiceType.VPC, {}),
        "public-subnet": (
            ServiceType.SUBNET,
            {"cidr_block": "10.0.1.0/24", "availability_zone": "us-east-1a"},
        ),
        "private-subnet": (
            ServiceType.SUBNET,
            {"cidr_block": "10.0.2.0/24", "availability_zone": "us-east-1b"},
        ),
        "web-security": (ServiceType.SECURITY_GROUP, {}),
        "ops-security": (ServiceType.SECURITY_GROUP, {}),
        "internet": (ServiceType.INTERNET_GATEWAY, {}),
        "nat": (ServiceType.NAT_GATEWAY, {"allocation_id": "eipalloc-12345678"}),
        "public-routes": (ServiceType.ROUTE_TABLE, {}),
        "private-routes": (ServiceType.ROUTE_TABLE, {}),
        "template": (ServiceType.EC2_LAUNCH_TEMPLATE, {"image_id": "ami-12345678"}),
        "workers": (ServiceType.EC2_AUTO_SCALING, {}),
    }
    payload = launch_architecture()
    payload["resources"] = [
        {
            "id": name,
            "name": name,
            "service_type": service.value,
            "config": minimal_config_for(service).model_dump(exclude_none=True)
            | config,
        }
        for name, (service, config) in nodes.items()
    ]
    edges = [
        *(
            ("network", name, "contains")
            for name in (
                "public-subnet",
                "private-subnet",
                "web-security",
                "ops-security",
                "internet",
                "public-routes",
                "private-routes",
            )
        ),
        ("public-subnet", "nat", "places"),
        ("public-subnet", "public-routes", "associates"),
        ("private-subnet", "private-routes", "associates"),
        ("internet", "public-routes", "routes_to"),
        ("nat", "private-routes", "routes_to"),
        ("web-security", "template", "associates"),
        ("ops-security", "template", "associates"),
        ("template", "workers", "launches"),
        ("public-subnet", "workers", "places"),
        ("private-subnet", "workers", "places"),
    ]
    payload["connections"] = [
        {
            "source": source,
            "source_id": source,
            "target": target,
            "target_id": target,
            "connection_type": kind,
            "connection_config": {},
        }
        for source, target, kind in edges
    ]
    return payload


def test_complete_phase_one_architecture_validates(tmp_path):
    from tests.test_generated_project_validates import (
        _init_args,
        _run_terraform,
        _write_tree,
        needs_terraform,
    )

    ir = project(networking_architecture())
    assert all(not preview.issues for preview in ConnectionPreviewer().preview_all(ir))
    tree = CodeGenerator().generate(ir)
    assert_tree_parses(tree)
    main = tree["connection-check/environments/dev/main.tf"]
    assert (
        "security_group_ids = [module.ops-security.security_group_id, module.web-security.security_group_id]"
        in main
    )
    assert (
        "subnet_ids = [module.private-subnet.subnet_id, module.public-subnet.subnet_id]"
        in main
    )
    assert "launch_template_id = module.template.launch_template_id" in main
    assert "vpc_id = module.network.vpc_id" in main
    if needs_terraform.args[0]:
        pytest.skip("terraform binary not installed")
    _write_tree(tmp_path, tree)
    environment = tmp_path / "connection-check/environments/dev"
    _run_terraform(_init_args(), environment)
    _run_terraform(["validate", "-no-color"], environment)
