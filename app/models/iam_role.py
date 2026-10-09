"""External role references retain their account, partition, and path identity."""

ROLE_ARN_PATTERN = (
    r"^arn:[^:]+:iam::[0-9]{12}:role/([A-Za-z0-9+=,.@_/-]+/)?[A-Za-z0-9+=,.@_-]{1,64}$"
)
