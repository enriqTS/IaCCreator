# OpenSearch index connections

Lambda and ECS support `reads_from` and `writes_to` connections to OpenSearch domains. Each connection requires an explicit lowercase `index_name`; wildcards, index lists, and paths are rejected. Read access is the default. Grants attach to the Lambda execution role or ECS task role.

The generated permissions apply to HTTP methods and paths under the selected index:

| Connection | Methods | Paths relative to the index |
|---|---|---|
| Read | GET, HEAD | `/_doc/*`, `/_search`, `/_count` |
| Read | POST | `/_search`, `/_count` |
| Write | PUT | `/_doc/*` |
| Write | POST | `/_doc`, `/_doc/*`, `/_update/*`, `/_bulk` |
| Write | DELETE | `/_doc/*` |

Search POST permissions do not grant document mutations. Write access includes document deletes and index-scoped bulk operations; it does not include search/read access, index creation/deletion APIs, mappings, settings, aliases, root bulk endpoints, or cluster administration. Add both connection types when an application requires both. Provision index mappings and settings separately; service-side automatic index creation may still occur during document writes.

Connected domains enforce HTTPS with TLS 1.2 or newer and set `rest.action.multi.allow_explicit_index` to the string `false`. This prevents bulk/multi-index request bodies from bypassing URL-based index scoping. The setting affects the entire domain, including other clients, and can disrupt OpenSearch Dashboards. Bulk clients must use the index-scoped URL and omit explicit index names from request bodies. See [AWS access-control considerations](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ac.html).

The domain module exports its ARN, HTTPS endpoint, and Region through application inputs. Consumers export an `opensearch_<domain-node-name>_<index-hash>` object containing `endpoint`, `region`, and `index_name`. Application code signs HTTPS requests using its runtime role, the `es` signing service, and the exported Region. No passwords, users, or secret values are generated or retrieved.

These are URL-scoped IAM grants, not fine-grained document authorization. Use a concrete index rather than an alias, and manage aliases separately. Existing domain policies or other identity policies may broaden or deny access; fine-grained security can require additional role mappings and impose further restrictions. This connection does not rewrite domain access policies or fine-grained authorization. Cross-account access additionally needs a domain-owner policy. Network routing and VPC access are separate. Clients that call root, health, or discovery APIs need separately configured permissions.

Multiple indexes and consumers share domain settings and metadata. Duplicate connections and reordered diagrams generate identical results. Domains without these connections retain their previous generated configuration.
