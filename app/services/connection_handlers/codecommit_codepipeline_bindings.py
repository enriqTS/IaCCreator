import json
import re

from app.exceptions import CrossRegionConnectionError, InvalidConnectionConfigError
from app.models.connection_configs.codecommit_codepipeline import (
    CodeCommitPipelineConfig,
)
from app.models.iam_role import ROLE_ARN_PATTERN
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler


def resolve_pipeline_source(
    connection: ConnectionIR, project: ProjectIR
) -> CodeCommitPipelineConfig:
    target = BaseConnectionHandler._find_instance(connection.target_name, project)
    peers = [
        peer
        for peer in project.connections
        if peer.target_name == target.name
        and peer.source_service == ServiceType.CODECOMMIT
    ]
    try:
        if len({peer.source_name for peer in peers}) != 1:
            raise ValueError(
                "One CodeCommit repository must own the pipeline source binding"
            )
        requests = [
            CodeCommitPipelineConfig.model_validate(peer.connection_config)
            for peer in peers
        ]
        if any(request != requests[0] for request in requests):
            raise ValueError(
                "Repeated repository-pipeline connections must agree on stage, action, and branch"
            )
        request = requests[0]
        if not re.fullmatch(ROLE_ARN_PATTERN, target.config.role_arn or ""):
            raise ValueError(
                "A repository source requires a valid external pipeline role ARN"
            )
        managed_store = any(
            peer.source_name == target.name
            and peer.connection_type == "stores_artifacts"
            for peer in project.connections
        )
        if not (target.config.artifact_bucket_name or "").strip() and not managed_store:
            raise ValueError(
                "A repository source requires an external or connected artifact store"
            )
        stages = json.loads(target.config.stages_json)
        if len(stages) < 2 or stages[0]["name"] != request.stage_name:
            raise ValueError("Select the pipeline's existing first source stage")
        matches = [
            action
            for action in stages[0]["actions"]
            if action["name"] == request.action_name
        ]
        if len(matches) != 1:
            raise ValueError("Select an existing source action in the first stage")
        action = matches[0]
        if (
            action["category"],
            action["owner"],
            action["provider"],
            action["version"],
        ) != ("Source", "AWS", "CodeCommit", "1"):
            raise ValueError(
                "The selected action must be an AWS CodeCommit version 1 source"
            )
        if action.get("role_arn") is not None or action.get("region") is not None:
            raise ValueError(
                "Selected source action role and region overrides are unsupported"
            )
        outputs = action["output_artifacts"]
        if (
            action["input_artifacts"]
            or len(outputs) != 1
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", outputs[0])
        ):
            raise ValueError(
                "A CodeCommit source requires zero inputs and one valid output artifact"
            )
        all_outputs = [
            output
            for stage in stages
            for item in stage["actions"]
            for output in item["output_artifacts"]
        ]
        if all_outputs.count(outputs[0]) != 1:
            raise ValueError(
                "The selected source output artifact must have one producer"
            )
        configuration = action["configuration"]
        if configuration.get("OutputArtifactFormat", "CODE_ZIP") != "CODE_ZIP" or set(
            configuration
        ) - {
            "RepositoryName",
            "BranchName",
            "PollForSourceChanges",
            "OutputArtifactFormat",
        }:
            raise ValueError("Only ZIP CodeCommit source configuration is supported")
    except ValueError as exc:
        raise InvalidConnectionConfigError(
            connection.source_name,
            target.name,
            connection.connection_type,
            [{"loc": ("repository_source",), "msg": str(exc)}],
        ) from exc
    source = BaseConnectionHandler._find_instance(connection.source_name, project)
    for environment in project.environments:
        override = environment.variables.get("region")
        source_region = (
            override or source.provider_region or project.global_config.provider_region
        )
        target_region = (
            override or target.provider_region or project.global_config.provider_region
        )
        if source_region != target_region:
            raise CrossRegionConnectionError(
                source.name,
                source_region,
                target.name,
                target_region,
                connection.connection_type,
            )
    return request
