"""Typed validation for pipeline stages entered as JSON in the editor."""

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class PipelineAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9.@_-]+$")
    category: Literal["Source", "Build", "Deploy", "Test", "Invoke", "Approval"]
    owner: Literal["AWS", "ThirdParty", "Custom"] = "AWS"
    provider: str = Field(min_length=1)
    version: str = "1"
    input_artifacts: list[str] = []
    output_artifacts: list[str] = []
    configuration: dict[str, str] = {}
    run_order: int = Field(default=1, ge=1, le=999)
    role_arn: str | None = None
    region: str | None = None


class PipelineStage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9.@_-]+$")
    actions: list[PipelineAction] = Field(min_length=1)


def normalize_stages(value: str) -> str:
    stages = TypeAdapter(list[PipelineStage]).validate_json(value)
    if stages:
        if len(stages) < 2 or len({stage.name for stage in stages}) != len(stages):
            raise ValueError("A pipeline requires at least two uniquely named stages")
        for stage in stages:
            if len({action.name for action in stage.actions}) != len(stage.actions):
                raise ValueError("Action names must be unique within each stage")
        if any(action.category != "Source" for action in stages[0].actions):
            raise ValueError("The first stage must contain source actions")
    return json.dumps([stage.model_dump(exclude_none=True) for stage in stages])
