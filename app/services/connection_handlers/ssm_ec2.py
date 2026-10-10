"""Document-owned associations consume policy-ready nodes without owning their profile."""

from app.generators.hcl_renderer import Expr
from app.generators.ssm_ec2 import render_associations, render_ssm_node
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.ec2_runtime_role import Ec2RuntimeRole
from app.services.connection_handlers.ssm_ec2_bindings import resolve_associations


class SsmEc2Handler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        bindings = resolve_associations(connection, project)
        peers = [
            c
            for c in project.connections
            if c.source_name == connection.source_name
            and c.connection_type == "associates"
        ]
        if connection is not peers[0]:
            return ConnectionContribution()
        source = connection.source_name
        values = {}
        result = ConnectionContribution()
        for binding in bindings:
            target = self._find_instance(binding.target, project)
            target.config._managed_ssm = True
            result.merge(Ec2RuntimeRole().build(target.name))
            result.resources.append(
                self._resource(
                    target.name,
                    "ssm_node.tf",
                    render_ssm_node(target.name, self._renderer),
                )
            )
            result.outputs.append(
                self._output(
                    target.name,
                    "ssm_node",
                    self._renderer.render_expression(
                        {
                            "id": Expr(f"aws_instance.{target.name}.id"),
                            "arn": Expr(f"aws_instance.{target.name}.arn"),
                            "profile_arn": Expr(
                                "aws_iam_instance_profile.runtime_secrets.arn"
                            ),
                        }
                    ),
                    "Native EC2 node with ready SSM core permissions",
                )
            )
            values[binding.key] = {
                "instance": Expr(f"module.{target.name}.ssm_node"),
                "utc_hour": binding.settings.utc_hour,
                "utc_minute": binding.settings.utc_minute,
                "apply_immediately": binding.settings.apply_immediately,
                "parameters": {
                    k: v.replace("${", "$${").replace("%{", "%%{")
                    for k, v in binding.parameters.items()
                },
            }
        result.inputs.append(
            ModuleInput(
                module=source,
                name="ec2_associations",
                type="map(object({ instance = object({ id = string, arn = string, profile_arn = string }), utc_hour = number, utc_minute = number, apply_immediately = bool, parameters = map(string) }))",
                value=self._renderer.render_expression(dict(sorted(values.items()))),
                description="Explicit nodes and daily execution settings",
            )
        )
        result.resources.append(
            self._resource(
                source,
                "ec2_associations.tf",
                render_associations(source, self._renderer),
            )
        )
        result.outputs.append(
            self._output(
                source,
                "ec2_associations",
                "{ for key, association in aws_ssm_association.ec2 : key => { id = association.association_id, arn = association.arn, document_version = association.document_version, schedule = association.schedule_expression } }",
                "Native State Manager association identities and pinned versions",
            )
        )
        return result

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        binding = next(
            b
            for b in resolve_associations(connection, project)
            if b.target == connection.target_name
        )
        timing = (
            "on creation or update and daily"
            if binding.settings.apply_immediately
            else "at the next scheduled interval and daily thereafter"
        )
        return [
            ConnectionIssue(
                severity="warning",
                message=f"Applying Terraform creates a State Manager association that can run document steps {timing} at {binding.settings.utc_hour:02d}:{binding.settings.utc_minute:02d} UTC. It targets only the connected instance and pins the native latest document version; document updates change that pin. The shared EC2 runtime profile receives AmazonSSMManagedInstanceCore, including regional core agent operations and broad Parameter Store reads; existing secret/EFS permissions remain. Parameters are ordinary configuration visible in state, not a secret channel; only declared String overrides are supported. Provision and start SSM Agent in a compatible AMI, enable instance credentials, and provide HTTPS/DNS access to regional Systems Manager endpoints separately. The profile does not prove the node is online or compatible, and Terraform does not wait for command success. State Manager uses its service-linked dispatch behavior because the provider does not expose AssociationDispatchAssumeRole; accounts requiring a custom dispatch role are unsupported. Document actions may need additional instance IAM, S3/KMS permissions, or OS access. Creating or updating this association may change guest state; deletion does not undo commands already run. Automation/Policy documents, tag targeting, arbitrary schedules, output buckets, and command-result verification remain outside this connection.",
            )
        ]
