"""Versioned benchmark dataset and result models."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agentloop.models import TestSuite


class BenchmarkModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BenchmarkTask(BenchmarkModel):
    task_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    difficulty: Literal["easy", "medium", "hard"]
    prompt: str = Field(min_length=1)
    evaluation_suite: TestSuite


class BenchmarkDataset(BenchmarkModel):
    schema_version: str
    dataset_id: str
    description: str
    tasks: list[BenchmarkTask] = Field(min_length=1)

    @model_validator(mode="after")
    def ensure_unique_task_ids(self) -> BenchmarkDataset:
        task_ids = [task.task_id for task in self.tasks]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("benchmark task_id values must be unique")
        return self

    @property
    def fingerprint(self) -> str:
        canonical = json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def load(cls, path: str | Path) -> BenchmarkDataset:
        content = Path(path).read_text(encoding="utf-8")
        return cls.model_validate_json(content)


class UsageMetrics(BenchmarkModel):
    model_calls: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)


class StrategyTaskResult(BenchmarkModel):
    task_id: str
    strategy: str
    success: bool
    internal_success: bool | None = None
    duration_ms: float = Field(ge=0)
    coding_rounds: int = Field(default=1, ge=0)
    debate_rounds: int = Field(default=0, ge=0)
    message: str
    code: str | None = None
    usage: UsageMetrics = Field(default_factory=UsageMetrics)


class AggregateMetrics(BenchmarkModel):
    strategy: str
    total_tasks: int = Field(ge=0)
    passed_tasks: int = Field(ge=0)
    pass_rate: float = Field(ge=0, le=1)
    average_duration_ms: float = Field(ge=0)
    average_model_calls: float = Field(ge=0)
    average_total_tokens: float = Field(ge=0)
    average_coding_rounds: float = Field(ge=0)


class BenchmarkReport(BenchmarkModel):
    dataset_id: str
    dataset_fingerprint: str
    created_at: str
    results: list[StrategyTaskResult]
    aggregates: list[AggregateMetrics]
