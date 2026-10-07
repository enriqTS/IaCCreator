"""Managed scrapers inherit native EKS networking and AWS's default jobs."""

from app.generators.hcl_renderer import Expr, HCLRenderer


def scrape_configuration_expression(configuration: str, interval: str) -> Expr:
    defaults = f"yamldecode({configuration})"
    return Expr(
        f'yamlencode(merge({defaults}, {{ global = merge(try({defaults}.global, {{}}), {{ scrape_interval = "${{{interval}}}s" }}) }}))'
    )


def scraper_preconditions(cluster: str) -> list[dict]:
    workspace = "each.value.workspace_arn"
    interval = "each.value.scrape_interval_seconds"
    vpc = f"{cluster}.vpc_config[0]"
    return [
        {
            "condition": Expr(
                f'try(contains(["API", "API_AND_CONFIG_MAP"], {cluster}.access_config[0].authentication_mode), false) && {vpc}.endpoint_private_access'
            ),
            "error_message": "Managed scrapers require EKS API authentication and private endpoint access.",
        },
        {
            "condition": Expr(
                f"length({vpc}.subnet_ids) >= 2 && length({vpc}.subnet_ids) <= 5"
            ),
            "error_message": "Managed scrapers require two to five native EKS subnets spanning at least two Availability Zones.",
        },
        {
            "condition": Expr(
                "data.aws_vpc.eks_prometheus.enable_dns_support && data.aws_vpc.eks_prometheus.enable_dns_hostnames"
            ),
            "error_message": "The EKS VPC must enable DNS support and DNS hostnames.",
        },
        {
            "condition": Expr(
                f'can(regex("^arn:[^:]+:aps:[^:]+:[0-9]{{12}}:workspace/ws-[0-9a-f-]+$", {workspace})) && alltrue([for index in [1, 3, 4] : try(split(":", {workspace})[index], "") == split(":", {cluster}.arn)[index]])'
            ),
            "error_message": "The native Prometheus workspace and EKS cluster must share their partition, Region, and account.",
        },
        {
            "condition": Expr(
                f"{interval} >= 30 && {interval} <= 3600 && floor({interval}) == {interval}"
            ),
            "error_message": "Scrape intervals must be whole seconds between 30 and 3600.",
        },
    ]


def render_eks_scrapers(name: str, renderer: HCLRenderer) -> str:
    cluster = f"aws_eks_cluster.{name}"
    content = (
        'data "aws_prometheus_default_scraper_configuration" "eks_prometheus" {}\n\n'
    )
    content += renderer.render_resource(
        "aws_vpc", "eks_prometheus", {"id": Expr(f"{cluster}.vpc_config[0].vpc_id")}
    ).replace("resource ", "data ", 1)
    return (
        content
        + "\n"
        + renderer.render_resource(
            "aws_prometheus_scraper",
            f"{name}_prometheus",
            {
                "for_each": Expr("var.prometheus_scraper_workspaces"),
                "source": {
                    "eks": {
                        "cluster_arn": Expr(f"{cluster}.arn"),
                        "subnet_ids": Expr(f"{cluster}.vpc_config[0].subnet_ids"),
                        "security_group_ids": [
                            Expr(f"{cluster}.vpc_config[0].cluster_security_group_id")
                        ],
                    }
                },
                "destination": {
                    "amp": {"workspace_arn": Expr("each.value.workspace_arn")}
                },
                "scrape_configuration": scrape_configuration_expression(
                    "data.aws_prometheus_default_scraper_configuration.eks_prometheus.configuration",
                    "each.value.scrape_interval_seconds",
                ),
                "lifecycle": {"precondition": scraper_preconditions(cluster)},
            },
        )
    )
