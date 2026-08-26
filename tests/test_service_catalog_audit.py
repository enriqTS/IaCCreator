"""Cross-layer service catalog consistency tests."""

from scripts.audit_service_catalog import audit, read_frontend_catalog


def test_frontend_and_backend_service_catalogs_match() -> None:
    assert audit() == []


def test_null_frontend_entries_are_explicitly_decorative() -> None:
    _, decorative = read_frontend_catalog()
    assert len(decorative) == 137
    assert all(category and name for category, name in decorative)
