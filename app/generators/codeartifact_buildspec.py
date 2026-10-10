from app.generators.hcl_renderer import Expr


def package_buildspec_preconditions() -> list[dict]:
    return [
        {
            "condition": Expr(
                'try(tostring(local.package_buildspec.version) == "0.2" && startswith(jsonencode(local.package_buildspec), "{") && startswith(jsonencode(try(local.package_buildspec.phases, {})), "{") && startswith(jsonencode(try(local.package_buildspec.phases.pre_build, {})), "{") && startswith(jsonencode(try(local.package_buildspec.phases.pre_build.commands, [])), "[") && alltrue([for command in try(local.package_buildspec.phases.pre_build.commands, []) : startswith(jsonencode(command), "\\"")]), false)'
            ),
            "error_message": "Package login requires an inline version 0.2 buildspec with object phases/pre_build and a string commands list; paths are unsupported.",
        }
    ]


def render_package_buildspec_locals() -> str:
    return (
        "\nlocals {\n"
        "  package_buildspec = try(yamldecode(var.buildspec), {})\n"
        '  package_login_command = format("aws codeartifact login --tool %s --domain %s --domain-owner %s --repository %s --region %s --duration-seconds 0", var.package_source.tool, var.package_source.domain_name, var.package_source.owner, var.package_source.repository_name, data.aws_region.package_source.region)\n'
        "  package_login_buildspec = try(yamlencode(merge(local.package_buildspec, { phases = merge(try(local.package_buildspec.phases, {}), { pre_build = merge(try(local.package_buildspec.phases.pre_build, {}), { commands = concat([local.package_login_command], try(local.package_buildspec.phases.pre_build.commands, [])) }) }) })), var.buildspec)\n"
        "}\n\n"
    )
