"""Stable Terraform identifiers shared by DMS endpoints and tasks."""

import hashlib


def dms_identifier(kind: str, value: str) -> str:
    return f"{kind}_" + hashlib.sha256(value.encode()).hexdigest()[:16]
