"""Redshift bindings scope credentials without mixing database/user pairs."""

import hashlib
import json
import re
from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.exceptions import InvalidConnectionConfigError
from app.generators.grafana_redshift import (
    redshift_data_sources_expression,
    redshift_scope_preconditions,
)
from app.models.input_models import ServiceType
from app.services.connection_handlers.registry import resolve_spec
from app.services.connection_previewer import ConnectionPreviewer
from tests.conftest import resource_name_st
from tests.generator_helpers import connection_architecture
from tests.test_cognito_api_gateway_connections import file_with, resources
from tests.test_generated_project_validates import (
    _init_args,
    _run_terraform,
    _write_tree,
    needs_terraform,
)
from tests.test_grafana_athena_connections import (
    connect_every_source,
    native_workgroup,
)
from tests.test_grafana_athena_connections import (
    evaluate as evaluate_athena,
)
from tests.test_kinesis_access_connections import generate, project


def architecture():
    return connection_architecture(
        resolve_spec(ServiceType.MANAGED_GRAFANA, ServiceType.REDSHIFT, None, {})
    )


def native_cluster(
    region="us-east-1", name="warehouse", database="application", user="grafana_reader"
):
    return {
        "arn": f"arn:aws:redshift:{region}:123456789012:cluster:{name}",
        "cluster_identifier": name,
        "region": region,
        "master_username": "administrator",
        "database_name": database,
        "database_user": user,
    }


def evaluate(tmp_path, expression, databases, partition="aws"):
    return evaluate_athena(
        tmp_path,
        expression.replace("var.redshift_databases", json.dumps(databases)),
        {"queries:application:records": native_workgroup()},
        partition,
    )


def connect_all_six_sources(payload):
    connect_every_source(payload)
    template = connection_architecture(
        resolve_spec(ServiceType.MANAGED_GRAFANA, ServiceType.ATHENA, None, {})
    )
    payload["resources"].append(
        dict(template["resources"][1], name="queries", id="queries")
    )
    payload["connections"].append(
        dict(template["connections"][0], target="queries", target_id="queries")
    )


def test_native_metadata_and_managed_password_preserve_module_ownership():
    tree = generate(architecture())
    cluster = resources(tree, "aws_redshift_cluster")[0]
    assert cluster["manage_master_password"] is True
    assert cluster["number_of_nodes"] == "${var.number_of_nodes}"
    assert "master_password" not in cluster
    assert "master_password_wo" not in cluster
    assert len(resources(tree, "aws_iam_role")) == 1
    assert len(resources(tree, "aws_iam_role_policy")) == 1
    main = file_with(tree, "/environments/dev/main.tf")
    for output in (
        "cluster_arn",
        "grafana_cluster_identifier",
        "grafana_cluster_region",
        "grafana_master_username",
    ):
        assert f"module.target-resource.{output}" in main
    target = file_with(tree, "/target-resource/outputs.tf")
    assert 'split(":", aws_redshift_cluster.target-resource.arn)[3]' in target
    assert "source-resource" not in target
    assert "master_password" not in target
    source = file_with(tree, "/source-resource/outputs.tf")
    assert 'output "redshift_data_sources"' in source
    assert "aws_iam_role_policy.source-resource_data_sources" in source
    assert not resources(tree, "aws_secretsmanager_secret_version")


def test_unconnected_clusters_keep_existing_password_behavior_and_optional_capacity():
    payload = architecture()
    payload["connections"] = []
    payload["resources"].pop(0)
    payload["resources"][0]["config"].pop("number_of_nodes")
    cluster = resources(generate(payload), "aws_redshift_cluster")[0]
    assert "manage_master_password" not in cluster
    assert "number_of_nodes" not in cluster


def test_two_workspaces_share_one_native_cluster_without_role_dependencies():
    payload = architecture()
    payload["resources"].append(
        dict(deepcopy(payload["resources"][0]), name="other", id="other")
    )
    payload["connections"].append(
        dict(payload["connections"][0], source="other", source_id="other")
    )
    tree = generate(payload)
    assert len(resources(tree, "aws_iam_role")) == 2
    assert len(resources(tree, "aws_redshift_cluster")) == 1
    target = file_with(tree, "/target-resource/outputs.tf")
    assert "source-resource" not in target
    assert "aws_iam_role" not in target


@given(
    bindings=st.lists(
        st.tuples(
            resource_name_st,
            st.from_regex(r"[a-z][a-z0-9_]{1,12}", fullmatch=True),
            st.from_regex(r"[a-z][a-z0-9_]{1,12}", fullmatch=True),
        ),
        min_size=1,
        max_size=6,
        unique=True,
    ),
    duplicate=st.booleans(),
)
@settings(max_examples=25)
def test_clusters_and_pairs_share_one_order_independent_role(bindings, duplicate):
    payload = architecture()
    target = payload["resources"].pop()
    connection = payload["connections"].pop()
    for name in sorted({name for name, _, _ in bindings}):
        payload["resources"].append(
            dict(deepcopy(target), name=f"data-{name}", id=name)
        )
    for name, database, user in bindings:
        payload["connections"].append(
            dict(
                connection,
                target=f"data-{name}",
                target_id=name,
                connection_config={"database_name": database, "database_user": user},
            )
        )
    tree = generate(payload)
    assert len(resources(tree, "aws_iam_role")) == 1
    assert len(resources(tree, "aws_redshift_cluster")) == len(
        {name for name, _, _ in bindings}
    )
    main = file_with(tree, "/environments/dev/main.tf")
    for name, database, user in bindings:
        assert f'"data-{name}:{database}:{user}" = ' in main
    payload["connections"] = list(
        reversed(payload["connections"] * (2 if duplicate else 1))
    )
    assert generate(payload) == tree


@pytest.mark.parametrize("field", ["database_name", "database_user"])
@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "*",
        "data*",
        "db/user",
        "UPPER",
        "${var.user}",
        "a" * 65,
        "1user",
        "a:user",
    ],
)
def test_missing_or_unscoped_selectors_are_rejected(field, value):
    payload = architecture()
    if value is None:
        payload["connections"][0]["connection_config"].pop(field)
    else:
        payload["connections"][0]["connection_config"][field] = value
    with pytest.raises(InvalidConnectionConfigError, match=field):
        generate(payload)


@pytest.mark.parametrize("field", ["node_type", "master_username"])
def test_clusters_require_explicit_creation_settings(field):
    payload = architecture()
    payload["resources"][1]["config"].pop(field)
    with pytest.raises(InvalidConnectionConfigError, match=field):
        generate(payload)


@pytest.mark.parametrize("user", ["administrator", "public"])
def test_master_and_public_users_are_rejected(user):
    payload = architecture()
    payload["connections"][0]["connection_config"]["database_user"] = user
    with pytest.raises(InvalidConnectionConfigError, match="non-administrator"):
        generate(payload)


def test_organization_workspaces_are_rejected():
    payload = architecture()
    payload["resources"][0]["config"]["account_access_type"] = "ORGANIZATION"
    with pytest.raises(InvalidConnectionConfigError, match="current-account"):
        generate(payload)


def test_preview_explains_database_permissions_and_shared_statement_access():
    preview = ConnectionPreviewer().preview_all(project(architecture()))[0]
    messages = " ".join(issue.message for issue in preview.issues)
    for text in (
        "read-only SQL grants",
        "superuser",
        "AWS-managed administrator password",
        "Data API eligible",
        "sessions and Grafana users",
        "Serverless",
    ):
        assert text in messages
    assert not preview.iam
    assert {item.module for item in preview.resources} == {"source-resource"}


@needs_terraform
@pytest.mark.parametrize(
    "mode,expected",
    [
        ("same", [True] * 4),
        ("cross_region", [True] * 4),
        ("cross_account", [True, False, True, True]),
        ("cross_partition", [True, False, True, True]),
        ("invalid_arn", [False, False, False, True]),
        ("wrong_region", [True, True, False, True]),
        ("wrong_identifier", [True, True, False, True]),
        ("wildcard_user", [True, True, True, False]),
        ("wildcard_database", [True, True, True, False]),
        ("master_user", [True, True, True, False]),
        ("public_user", [True, True, True, False]),
        ("empty", [False, True, True, True]),
    ],
)
def test_native_guards_reject_scope_mismatches(tmp_path, mode, expected):
    native = native_cluster()
    if mode == "cross_region":
        native = native_cluster(region="eu-west-1")
    elif mode == "cross_account":
        native["arn"] = native["arn"].replace("123456789012", "999999999999")
    elif mode == "cross_partition":
        native["arn"] = native["arn"].replace("arn:aws:", "arn:aws-cn:")
    elif mode == "invalid_arn":
        native["arn"] = "invalid"
    elif mode == "wrong_region":
        native["region"] = "eu-west-1"
    elif mode == "wrong_identifier":
        native["cluster_identifier"] = "another"
    elif mode == "wildcard_user":
        native["database_user"] = "user*"
    elif mode == "wildcard_database":
        native["database_name"] = "data*"
    elif mode == "master_user":
        native["master_username"] = "GRAFANA_READER"
    elif mode == "public_user":
        native["database_user"] = "public"
    expression = (
        "["
        + ", ".join(str(item["condition"]) for item in redshift_scope_preconditions())
        + "]"
    )
    assert (
        evaluate(
            tmp_path, expression, {} if mode == "empty" else {"data:app:user": native}
        )
        == expected
    )


@needs_terraform
@pytest.mark.parametrize("mixed", [False, True])
@pytest.mark.parametrize("partition", ["aws", "aws-cn"])
def test_serialized_iam_uses_native_clusters_and_separate_credential_pairs(
    tmp_path, mixed, partition
):
    payload = architecture()
    if mixed:
        connect_all_six_sources(payload)
    text = file_with(generate(payload), "/source-resource/data_source_role.tf")
    expression = re.search(
        r"\n  policy = (jsonencode\(.*?\))\n  lifecycle", text, re.S
    ).group(1)
    databases = {
        "data:application:reader": native_cluster(user="reader"),
        "data:analytics:analyst": native_cluster(database="analytics", user="analyst"),
        "remote:archive:auditor": native_cluster(
            region="eu-west-1", name="archive", database="archive", user="auditor"
        ),
    }
    databases = {
        key: dict(db, arn=db["arn"].replace("arn:aws:", f"arn:{partition}:"))
        for key, db in databases.items()
    }
    policy = json.loads(evaluate(tmp_path, expression, databases, partition))
    statements = policy["Statement"]
    by_sid = {item["Sid"]: item for item in statements if "Sid" in item}
    query = by_sid["RedshiftClusterQueries"]
    assert set(query["Resource"]) == {db["arn"] for db in databases.values()}
    assert "redshift-data:ExecuteStatement" in query["Action"]
    credentials = [
        item
        for item in statements
        if item["Action"] == ["redshift:GetClusterCredentials"]
    ]
    assert len(credentials) == len(databases)
    for statement in credentials:
        conditions = statement["Condition"]["StringEquals"]
        selected = [
            db
            for db in databases.values()
            if db["database_name"] == conditions["redshift:DbName"]
            and db["database_user"] == conditions["redshift:DbUser"]
        ]
        assert len(selected) == 1
        db = selected[0]
        base = f"arn:{partition}:redshift:{db['region']}:123456789012:"
        assert set(statement["Resource"]) == {
            f"{base}dbuser:{db['cluster_identifier']}/{db['database_user']}",
            f"{base}dbname:{db['cluster_identifier']}/{db['database_name']}",
        }
    results = by_sid["RedshiftStatementResults"]
    assert results["Resource"] == "*"
    assert set(results["Condition"]["StringEquals"]["aws:RequestedRegion"]) == {
        "us-east-1",
        "eu-west-1",
    }
    assert "redshift-data:statement-owner-iam-userid" not in json.dumps(results)
    actions = {action for item in statements for action in item["Action"]}
    assert (
        not {
            "redshift:GetClusterCredentialsWithIAM",
            "redshift:CreateClusterUser",
            "redshift:JoinGroup",
            "redshift:ModifyCluster",
            "secretsmanager:GetSecretValue",
            "redshift-serverless:GetCredentials",
            "redshift-data:BatchExecuteStatement",
        }
        & actions
    )
    assert ("AthenaWorkgroupQueries" in by_sid) is mixed
    assert ("OpenSearchMultiSearch" in by_sid) is mixed


@needs_terraform
def test_plugin_settings_and_uids_use_native_database_user_identities(tmp_path):
    first = native_cluster(region="eu-west-1")
    databases = {
        "data:application:grafana_reader": first,
        "data:application:analyst": dict(first, database_user="analyst"),
    }
    expression = str(redshift_data_sources_expression())
    payloads = evaluate(tmp_path, expression, databases)
    for binding, item in payloads.items():
        db = databases[binding]
        assert item == {
            "name": binding,
            "uid": "rs-"
            + hashlib.sha256(
                f"{db['arn']}/database/{db['database_name']}/user/{db['database_user']}".encode()
            ).hexdigest()[:16],
            "type": "grafana-redshift-datasource",
            "access": "proxy",
            "jsonData": {
                "authType": "default",
                "defaultRegion": "eu-west-1",
                "clusterIdentifier": "warehouse",
                "database": "application",
                "dbUser": db["database_user"],
                "useServerless": False,
                "useManagedSecret": False,
                "withEvent": False,
            },
        }
    renamed = evaluate(
        tmp_path, expression, {"renamed:application:grafana_reader": first}
    )
    assert (
        renamed["renamed:application:grafana_reader"]["uid"]
        == payloads["data:application:grafana_reader"]["uid"]
    )
    assert len({item["uid"] for item in payloads.values()}) == 2


@needs_terraform
def test_long_bindings_keep_full_selectors_and_bounded_unique_names(tmp_path):
    database, user = "d" * 64, "u" * 64
    databases = {
        f"{'node' * 32}:{database}:{user}": native_cluster(
            database=database, user=user
        ),
        f"{'node' * 32}:{database}:{user[:-1]}v": native_cluster(
            database=database, user=user[:-1] + "v"
        ),
    }
    payloads = evaluate(tmp_path, str(redshift_data_sources_expression()), databases)
    assert len({item["name"] for item in payloads.values()}) == 2
    for binding, item in payloads.items():
        assert len(item["name"]) <= 190
        assert item["jsonData"]["database"] == database
        assert item["jsonData"]["dbUser"] == binding.split(":")[2]


@needs_terraform
@pytest.mark.terraform
@pytest.mark.parametrize(
    "mode", ["plain", "cross_region", "multiple_pairs", "shared_cluster", "mixed"]
)
def test_projects_validate_and_have_acyclic_shared_role_graphs(tmp_path, mode):
    payload = architecture()
    if mode == "cross_region":
        payload["resources"][1]["provider_region"] = "eu-west-1"
    elif mode == "multiple_pairs":
        payload["connections"].append(
            dict(
                payload["connections"][0],
                connection_config={
                    "database_name": "analytics",
                    "database_user": "analyst",
                },
            )
        )
    elif mode == "mixed":
        connect_all_six_sources(payload)
    elif mode == "shared_cluster":
        payload["resources"].append(
            dict(deepcopy(payload["resources"][0]), name="other", id="other")
        )
        payload["connections"].append(
            dict(payload["connections"][0], source="other", source_id="other")
        )
    tree = generate(payload)
    _write_tree(tmp_path, tree)
    path = tmp_path / next(
        path for path in tree if path.endswith("/environments/dev/main.tf")
    )
    _run_terraform(
        [arg for arg in _init_args() if arg != "-backend=false"], path.parent
    )
    _run_terraform(["validate", "-no-color"], path.parent)
    _run_terraform(["graph", "-type=plan"], path.parent)
