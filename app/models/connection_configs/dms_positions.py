"""Native CDC position formats are shared by schema and source validation."""

MYSQL_POSITION_PATTERN = r"[A-Za-z0-9_-][A-Za-z0-9_.-]{0,249}\.[0-9]+:[0-9]+"
POSTGRES_POSITION_PATTERN = r"[0-9A-Fa-f]{1,8}/[0-9A-Fa-f]{1,8}"
