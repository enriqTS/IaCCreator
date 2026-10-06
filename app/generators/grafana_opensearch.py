"""Grafana OpenSearch payloads use native versions and domain-scoped multi-search."""

from app.generators.hcl_renderer import Expr


def opensearch_scope_preconditions() -> list[dict]:
    return [
        {
            "condition": Expr(
                'length(var.opensearch_sources) > 0 && alltrue([for source in values(var.opensearch_sources) : can(regex("^arn:[^:]+:es:[^:]+:[0-9]{12}:domain/[a-z][a-z0-9-]{2,27}$", source.arn)) && can(regex("^[a-z0-9][a-z0-9_.-]{0,254}$", source.index_name)) && can(regex("^[A-Za-z_@][A-Za-z0-9_.@-]{0,254}$", source.time_field))])'
            ),
            "error_message": "Grafana requires native OpenSearch domain ARNs, concrete default indexes, and valid time fields.",
        },
        {
            "condition": Expr(
                'alltrue([for source in values(var.opensearch_sources) : try(split(":", source.arn)[1], "") == data.aws_partition.grafana_sources.partition && try(split(":", source.arn)[4], "") == data.aws_caller_identity.grafana_sources.account_id])'
            ),
            "error_message": "Grafana and connected OpenSearch domains must use the same partition and account.",
        },
        {
            "condition": Expr(
                'alltrue([for source in values(var.opensearch_sources) : source.region == try(split(":", source.arn)[3], "") && source.domain_name == try(split("/", source.arn)[1], "") && can(regex("^(search|vpc)-[a-z0-9-]+[.][a-z0-9-]+[.]es[.][a-z0-9.]+$", source.endpoint)) && (startswith(source.endpoint, "search-${source.domain_name}-") || startswith(source.endpoint, "vpc-${source.domain_name}-")) && endswith(source.endpoint, ".${source.region}.es.${data.aws_partition.grafana_sources.dns_suffix}")])'
            ),
            "error_message": "OpenSearch endpoints, domain names, and signing Regions must match their native domain identities.",
        },
        {
            "condition": Expr(
                'alltrue([for source in values(var.opensearch_sources) : can(regex("^(OpenSearch|Elasticsearch)_[0-9]+[.][0-9]+([.][0-9]+)?$", source.engine_version)) && source.allow_explicit_index == "true"])'
            ),
            "error_message": "Grafana requires a native engine version and explicit request-body indexes for root multi-search.",
        },
    ]


def opensearch_query_statements() -> list[dict]:
    return [
        {
            "Sid": "OpenSearchVersion",
            "Effect": "Allow",
            "Action": "es:ESHttpGet",
            "Resource": Expr(
                'distinct([for source in values(var.opensearch_sources) : "${source.arn}/"])'
            ),
        },
        {
            "Sid": "OpenSearchIndexMetadata",
            "Effect": "Allow",
            "Action": "es:ESHttpGet",
            "Resource": Expr(
                'distinct(flatten([for source in values(var.opensearch_sources) : ["${source.arn}/${source.index_name}/_mapping", "${source.arn}/${source.index_name}/_mapping/*", "${source.arn}/${source.index_name}/_field_caps", "${source.arn}/${source.index_name}/_settings/index.number_of_shards"]]))'
            ),
        },
        {
            "Sid": "OpenSearchMultiSearch",
            "Effect": "Allow",
            "Action": "es:ESHttpPost",
            "Resource": Expr(
                'distinct([for source in values(var.opensearch_sources) : "${source.arn}/_msearch"])'
            ),
        },
    ]


def opensearch_data_sources_expression() -> Expr:
    return Expr("""{
    for binding, source in var.opensearch_sources : binding => {
      name = length(binding) <= 190 ? binding : "${substr(binding, 0, 173)}-${substr(sha256(binding), 0, 16)}"
      uid = "os-${substr(sha256("${source.arn}/index/${source.index_name}"), 0, 16)}"
      type = "grafana-opensearch-datasource"
      access = "proxy"
      url = "https://${source.endpoint}"
      jsonData = {
        flavor = startswith(source.engine_version, "OpenSearch_") ? "opensearch" : "elasticsearch"
        version = join(".", slice(concat(split(".", split("_", source.engine_version)[1]), ["0"]), 0, 3))
        database = source.index_name
        timeField = source.time_field
        timeInterval = "10s"
        pplEnabled = false
        serverless = false
        sigV4Auth = true
        sigV4AuthType = "default"
        sigV4Region = source.region
      }
    }
  }""")
