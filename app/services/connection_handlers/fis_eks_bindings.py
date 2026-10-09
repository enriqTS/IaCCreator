"""Cluster access aggregates shared principals independently of target selectors."""

import hashlib
import re
from dataclasses import dataclass

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_configs.fis_eks import FisEksConfig
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.fis_bindings import (
    experiment_binding_errors,
    validate_experiment_regions,
)


@dataclass(frozen=True)
class FisEksBinding:
    target: str
    settings: FisEksConfig
    service_account: str
    kubernetes_group: str


def resolve_eks_fault(connection: ConnectionIR, project: ProjectIR) -> FisEksBinding:
    source = BaseConnectionHandler._find_instance(connection.source_name, project)
    peers = [
        item
        for item in project.connections
        if item.source_name == source.name
        and item.source_service == ServiceType.FAULT_INJECTION_SIMULATOR
        and item.target_service == ServiceType.EKS
        and item.connection_type == "targets"
    ]
    request = FisEksConfig.model_validate(connection.connection_config)
    targets = tuple(sorted({item.target_name for item in peers}))
    errors = experiment_binding_errors(connection, project)
    if len(targets) != 1:
        errors.append(
            {
                "loc": ("target",),
                "msg": "Each pod-delete template must target exactly one connected EKS cluster",
            }
        )
    if any(
        FisEksConfig.model_validate(item.connection_config) != request for item in peers
    ):
        errors.append(
            {
                "loc": ("connection_config",),
                "msg": "Repeated EKS connections must select the same namespace, deployment, and pod selection",
            }
        )
    for name in targets:
        cluster = BaseConnectionHandler._find_instance(name, project)
        if cluster.config.authentication_mode == "CONFIG_MAP":
            errors.append(
                {
                    "loc": ("authentication_mode",),
                    "msg": "FIS pod actions require API or API_AND_CONFIG_MAP authentication",
                }
            )
        version = cluster.config.eks_version
        if version and (
            not re.fullmatch(r"[0-9]+\.[0-9]+", version)
            or tuple(map(int, version.split("."))) < (1, 30)
        ):
            errors.append(
                {
                    "loc": ("eks_version",),
                    "msg": "FIS pod actions require Kubernetes 1.30 or newer",
                }
            )
    if errors:
        raise InvalidConnectionConfigError(
            source.name, connection.target_name, connection.connection_type, errors
        )
    validate_experiment_regions(connection, targets, project)
    identity = connection.source_id or source.name
    service_account = (
        "iacc-fis-"
        + hashlib.sha256(f"{identity}:{source.config.role_arn}".encode()).hexdigest()[
            :12
        ]
    )
    group = (
        "iacc-fis-" + hashlib.sha256(source.config.role_arn.encode()).hexdigest()[:12]
    )
    return FisEksBinding(targets[0], request, service_account, group)


def experiment_role_sources(cluster: str, project: ProjectIR) -> dict[str, str]:
    sources = {}
    for connection in sorted(project.connections, key=lambda item: item.source_name):
        if (
            connection.source_service != ServiceType.FAULT_INJECTION_SIMULATOR
            or connection.target_service != ServiceType.EKS
            or connection.connection_type != "targets"
            or connection.target_name != cluster
        ):
            continue
        source = BaseConnectionHandler._find_instance(connection.source_name, project)
        role = source.config.role_arn
        key = "role_" + hashlib.sha256(role.encode()).hexdigest()[:12]
        sources.setdefault(key, source.name)
    return dict(sorted(sources.items()))
