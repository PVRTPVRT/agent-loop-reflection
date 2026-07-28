"""V2 evaluation models with first-class expected exception support."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvaluationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvaluationCase(EvaluationModel):
    args: list[Any]
    expected: Any | None
    expected_exception: str | None
    description: str = ""

    @model_validator(mode="after")
    def validate_outcome(self) -> EvaluationCase:
        if self.expected_exception is not None and self.expected is not None:
            raise ValueError("expected must be null when expected_exception is provided")
        if self.expected_exception is not None:
            if not self.expected_exception.isidentifier():
                raise ValueError("expected_exception must be an exception class name")
            if not self.expected_exception.endswith(("Error", "Exception")):
                raise ValueError("expected_exception must end with Error or Exception")
        return self


class EvaluationSuite(EvaluationModel):
    function_name: str = Field(min_length=1)
    test_cases: list[EvaluationCase] = Field(min_length=1)

    @model_validator(mode="after")
    def ensure_unique_cases(self) -> EvaluationSuite:
        serialized = [
            json.dumps(case.args, ensure_ascii=False, sort_keys=True) for case in self.test_cases
        ]
        if len(serialized) != len(set(serialized)):
            raise ValueError("test_cases must not contain duplicate args")
        return self


class EvaluationTask(EvaluationModel):
    task_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    difficulty: Literal["easy", "medium", "hard"]
    prompt: str = Field(min_length=1)
    evaluation_suite: EvaluationSuite


class EvaluationDataset(EvaluationModel):
    schema_version: Literal["2.0"]
    dataset_id: str = Field(min_length=1)
    description: str
    tasks: list[EvaluationTask] = Field(min_length=1)

    @model_validator(mode="after")
    def ensure_unique_task_ids(self) -> EvaluationDataset:
        task_ids = [task.task_id for task in self.tasks]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("task_id values must be unique")
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
    def load(cls, path: str | Path) -> EvaluationDataset:
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))
