"""Versioned public task contracts that do not reveal hidden test values."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ParameterContract(ContractModel):
    name: str = Field(min_length=1)
    domain: str = Field(min_length=1)


class TaskContract(ContractModel):
    function_name: str = Field(min_length=1)
    parameters: list[ParameterContract]
    returns: str = Field(min_length=1)
    errors: list[str]


class ContractRegistry(ContractModel):
    schema_version: str
    dataset_id: str
    contracts: dict[str, TaskContract]

    @model_validator(mode="after")
    def require_contracts(self) -> ContractRegistry:
        if not self.contracts:
            raise ValueError("contracts must not be empty")
        return self

    @classmethod
    def load(cls, path: str | Path) -> ContractRegistry:
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))

    def require(self, task_id: str) -> TaskContract:
        try:
            return self.contracts[task_id]
        except KeyError as exc:
            raise ValueError(f"No public contract found for task {task_id!r}") from exc


DEFAULT_CONTRACT_PATH = Path("benchmarks/contracts/coding-v1-contracts.json")


def contract_prompt(contract: TaskContract) -> str:
    return json.dumps(contract.model_dump(mode="json"), ensure_ascii=False, indent=2)
