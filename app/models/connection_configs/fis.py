"""Experiment target selection and action identifiers share bounded syntax."""

SELECTION_MODES = [f"COUNT({count})" for count in range(1, 6)] + ["ALL"]
ACTION_NAME_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"
