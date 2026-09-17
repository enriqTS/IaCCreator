"""CDC engine families share native position and authentication requirements."""

from dataclasses import dataclass

from app.models.connection_configs.dms_positions import (
    MYSQL_POSITION_PATTERN,
    ORACLE_POSITION_PATTERN,
    POSTGRES_POSITION_PATTERN,
    SQLSERVER_POSITION_PATTERN,
)


@dataclass(frozen=True)
class DmsCdcPolicy:
    engines: tuple[str, ...]
    label: str
    position_pattern: str
    position_description: str
    requires_secret: bool = False
    minimum_version: str | None = None
    version_pattern: str | None = None


MYSQL_CDC = DmsCdcPolicy(
    ("mysql", "mariadb", "aurora-mysql"),
    "MySQL",
    MYSQL_POSITION_PATTERN,
    "a native binlog filename and position",
)
POSTGRES_CDC = DmsCdcPolicy(
    ("postgres", "aurora-postgresql"),
    "PostgreSQL",
    POSTGRES_POSITION_PATTERN,
    "a native WAL LSN such as 4AF/B00000D0",
    requires_secret=True,
)
SQLSERVER_CDC = DmsCdcPolicy(
    ("sqlserver-ee", "sqlserver-se"),
    "SQL Server",
    SQLSERVER_POSITION_PATTERN,
    "a native SQL Server LSN such as 00000014:00000061:0001",
    requires_secret=True,
    minimum_version="3.5.3",
    version_pattern=r"^(([4-9]|[1-9][0-9]+)\.[0-9]+\.[0-9]+|3\.([6-9]|[1-9][0-9]+)\.[0-9]+|3\.5\.([3-9]|[1-9][0-9]+))(\.[0-9]+)*$",
)
ORACLE_CDC = DmsCdcPolicy(
    ("oracle-ee", "oracle-se2"),
    "Oracle",
    ORACLE_POSITION_PATTERN,
    "a native Oracle SCN expressed as a positive decimal integer",
    requires_secret=True,
)
CDC_SOURCE_POLICIES = {
    engine: policy
    for policy in (MYSQL_CDC, POSTGRES_CDC, SQLSERVER_CDC, ORACLE_CDC)
    for engine in policy.engines
}
