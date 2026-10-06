"""Resolved issuing authority and key selection for an ACM certificate."""

from dataclasses import dataclass

RSA_CA_KEYS = ("RSA_2048", "RSA_3072", "RSA_4096")
ECDSA_CA_KEYS = ("EC_prime256v1", "EC_secp384r1")
RSA_SIGNATURES = ("SHA256WITHRSA", "SHA384WITHRSA", "SHA512WITHRSA")
ECDSA_SIGNATURES = ("SHA256WITHECDSA", "SHA384WITHECDSA", "SHA512WITHECDSA")


@dataclass(frozen=True)
class PrivateCertificateBinding:
    authority_name: str
    key_algorithm: str
