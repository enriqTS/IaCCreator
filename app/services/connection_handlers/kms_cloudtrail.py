"""CloudTrail uses the shared key-policy owner with scoped trail identities."""

from app.services.connection_handlers.kms_encryption import KmsEncryptionHandler


class KmsCloudTrailHandler(KmsEncryptionHandler):
    def __init__(self) -> None:
        super().__init__("kms_key_id")
