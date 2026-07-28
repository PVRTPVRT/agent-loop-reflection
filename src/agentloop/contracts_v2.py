"""Machine-checkable public contracts for generated evaluation suites."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContractV2Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ParameterContractV2(ContractV2Model):
    name: str = Field(min_length=1)
    types: list[
        Literal[
            "integer",
            "float",
            "string",
            "boolean",
            "list",
            "object",
            "null",
        ]
    ] = Field(min_length=1)
    finite: bool | None = None
    items_hashable: bool | None = None


class ExceptionRule(ContractV2Model):
    parameter: str
    operator: Literal["<", "<=", ">", ">=", "==", "!="]
    value: Any | None = None
    other_parameter: str | None = None
    exception: str


class TaskContractV2(ContractV2Model):
    function_name: str = Field(min_length=1)
    oracle: str = Field(min_length=1)
    parameters: list[ParameterContractV2]
    exceptions: list[ExceptionRule]
    dynamic_exceptions: list[str] = Field(default_factory=list)

    @field_validator("dynamic_exceptions")
    @classmethod
    def validate_dynamic_exceptions(cls, exceptions: list[str]) -> list[str]:
        if len(exceptions) != len(set(exceptions)):
            raise ValueError("dynamic_exceptions must be unique")
        for exception in exceptions:
            if not exception.isidentifier() or not exception.endswith(
                ("Error", "Exception")
            ):
                raise ValueError(
                    "dynamic_exceptions must contain exception class names"
                )
        return exceptions


class ContractRegistryV2(ContractV2Model):
    schema_version: Literal["2.0"]
    dataset_id: str
    contracts: dict[str, TaskContractV2]

    @classmethod
    def load(cls, path: str | Path) -> ContractRegistryV2:
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))

    def require(self, task_id: str) -> TaskContractV2:
        try:
            return self.contracts[task_id]
        except KeyError as exc:
            raise ValueError(f"No V2 contract found for task {task_id!r}") from exc


DEFAULT_V2_CONTRACT_PATH = Path("benchmarks/contracts/coding-v2-contracts.json")


def render_contract(contract: TaskContractV2) -> str:
    public_data = contract.model_dump(mode="json", exclude={"oracle"})
    return json.dumps(public_data, ensure_ascii=False, indent=2)
