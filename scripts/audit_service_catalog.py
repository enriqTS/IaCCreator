"""Audit frontend AWS icons against the backend service capability catalog."""

import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.input_models import ServiceType  # noqa: E402
from app.services.service_catalog import SERVICE_CATALOG  # noqa: E402

CATALOG_PATH = Path("frontend/src/data/aws-icon-registry.ts")
_CATEGORY_PATTERN = re.compile(r"^\s+name: '([^']+)',\s*$")
_SERVICE_PATTERN = re.compile(
    r"\{ name: '([^']+)', .* serviceType: (null|'([^']+)') \}"
)


def read_frontend_catalog(
    path: Path = CATALOG_PATH,
) -> tuple[dict[str, list[str]], list[tuple[str, str]]]:
    typed: dict[str, list[str]] = defaultdict(list)
    decorative: list[tuple[str, str]] = []
    category = ""
    for line in path.read_text().splitlines():
        category_match = _CATEGORY_PATTERN.match(line)
        if category_match:
            category = category_match.group(1)
        service_match = _SERVICE_PATTERN.search(line)
        if not service_match:
            continue
        name, marker, service_type = service_match.groups()
        if marker == "null":
            decorative.append((category, name))
        else:
            typed[service_type].append(f"{category}/{name}")
    return dict(typed), decorative


def audit() -> list[str]:
    typed, decorative = read_frontend_catalog()
    errors: list[str] = []
    backend_types = {service.value for service in ServiceType}
    frontend_types = set(typed)
    for service_type in sorted(frontend_types - backend_types):
        errors.append(f"frontend service type is absent from backend: {service_type}")
    for service_type in sorted(backend_types - frontend_types):
        errors.append(f"backend service type is absent from frontend: {service_type}")
    if set(SERVICE_CATALOG) != set(ServiceType):
        errors.append("backend capability catalog does not classify every service type")

    duplicates = {key: values for key, values in typed.items() if len(values) > 1}
    print(f"Typed service types: {len(typed)}")
    print(f"Explicit decorative icons (serviceType null): {len(decorative)}")
    if duplicates:
        print("Aliases and duplicate icon mappings:")
        for service_type, locations in sorted(duplicates.items()):
            print(f"  {service_type}: {', '.join(locations)}")
    return errors


def main() -> int:
    errors = audit()
    for error in errors:
        print(f"ERROR: {error}")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
