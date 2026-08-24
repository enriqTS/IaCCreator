"""Naming rules for resources, shared by validation and the schema served to the editor."""

from __future__ import annotations

import re

# Names become Terraform resource labels, module names and directory names, so they must
# be valid HCL identifiers: a letter or underscore first, then letters, digits, _ or -.
RESOURCE_NAME_PATTERN = r"^[A-Za-z_][A-Za-z0-9_-]*$"

RESOURCE_NAME_DESCRIPTION = (
    "Must start with a letter or underscore and contain only letters, digits, "
    "underscores or hyphens"
)

RESOURCE_NAME_MAX_LENGTH = 64

_RESOURCE_NAME = re.compile(RESOURCE_NAME_PATTERN)


def is_valid_resource_name(name: str) -> bool:
    """Return whether a name is usable as a Terraform identifier and directory name."""
    return (
        bool(name)
        and len(name) <= RESOURCE_NAME_MAX_LENGTH
        and bool(_RESOURCE_NAME.match(name))
    )


# Words the editor should shout rather than capitalise, so labels read as AWS writes them
_ACRONYMS = frozenset(
    {
        "acl",
        "alb",
        "ami",
        "api",
        "arn",
        "asg",
        "aws",
        "az",
        "cidr",
        "cors",
        "cpu",
        "csv",
        "db",
        "dns",
        "ebs",
        "ec2",
        "ecr",
        "ecs",
        "efs",
        "eks",
        "elb",
        "gb",
        "http",
        "https",
        "iam",
        "id",
        "iops",
        "ip",
        "jwt",
        "kb",
        "kms",
        "mb",
        "mfa",
        "ms",
        "nat",
        "nlb",
        "oidc",
        "rds",
        "s3",
        "saml",
        "sms",
        "sns",
        "sqs",
        "sse",
        "ssl",
        "sts",
        "tls",
        "ttl",
        "uri",
        "url",
        "vpc",
        "vpn",
        "ws",
        "xml",
        "yaml",
    }
)


def _label_word(word: str) -> str:
    """Shout a word the industry writes in capitals, keeping a plural s lowercase."""
    if word in _ACRONYMS:
        return word.upper()
    if word.endswith("s") and word[:-1] in _ACRONYMS:
        return word[:-1].upper() + "s"
    return word


def field_label(field_name: str) -> str:
    """Turn a snake_case field name into the short label the editor shows above it."""
    words = [word for word in field_name.split("_") if word]
    if not words:
        return field_name
    parts = [_label_word(word) for word in words]
    if parts[0] == words[0]:
        parts[0] = parts[0][:1].upper() + parts[0][1:]
    return " ".join(parts)
