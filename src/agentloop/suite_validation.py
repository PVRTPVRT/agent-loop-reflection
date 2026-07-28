"""Validate generated V2 suites against public domains and trusted outcomes."""

from __future__ import annotations

import math
import operator
from typing import Any

from agentloop.contracts_v2 import (
    ExceptionRule,
    ParameterContractV2,
    TaskContractV2,
)
from agentloop.evaluation_v2_models import EvaluationSuite
from agentloop.oracles import ORACLES

OPERATORS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}


class SuiteContractError(ValueError):
    """Raised when a generated suite violates its public contract."""


def _matches_type(value: Any, type_name: str) -> bool:
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "float":
        return isinstance(value, float)
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "list":
        return isinstance(value, list)
    return value is None


def _validate_parameter(value: Any, contract: ParameterContractV2) -> None:
    if not any(_matches_type(value, type_name) for type_name in contract.types):
        raise SuiteContractError(
            f"{contract.name} has value {value!r}, outside types {contract.types}"
        )
    if contract.finite and isinstance(value, float) and not math.isfinite(value):
        raise SuiteContractError(f"{contract.name} must be finite")
    if contract.items_hashable and isinstance(value, list):
        for item in value:
            try:
                hash(item)
            except TypeError as exc:
                raise SuiteContractError(
                    f"{contract.name} contains unhashable item {item!r}"
                ) from exc


def _matching_exception(
    args_by_name: dict[str, Any],
    rules: list[ExceptionRule],
) -> str | None:
    for rule in rules:
        left = args_by_name[rule.parameter]
        right = (
            args_by_name[rule.other_parameter] if rule.other_parameter is not None else rule.value
        )
        if OPERATORS[rule.operator](left, right):
            return rule.exception
    return None


def validate_suite(
    suite: EvaluationSuite,
    contract: TaskContractV2,
) -> EvaluationSuite:
    if suite.function_name != contract.function_name:
        raise SuiteContractError(f"function_name must be {contract.function_name!r}")
    oracle = ORACLES.get(contract.oracle)
    if oracle is None:
        raise SuiteContractError(f"Unknown trusted oracle {contract.oracle!r}")

    for index, case in enumerate(suite.test_cases, 1):
        if len(case.args) != len(contract.parameters):
            raise SuiteContractError(
                f"case {index} has {len(case.args)} args; expected {len(contract.parameters)}"
            )
        args_by_name = {}
        for value, parameter in zip(case.args, contract.parameters, strict=True):
            _validate_parameter(value, parameter)
            args_by_name[parameter.name] = value

        required_exception = _matching_exception(args_by_name, contract.exceptions)
        if case.expected_exception != required_exception:
            raise SuiteContractError(
                f"case {index} expected_exception must be "
                f"{required_exception!r}, got {case.expected_exception!r}"
            )
        if required_exception is not None:
            continue

        try:
            oracle_value = oracle(*case.args)
        except Exception as exc:
            raise SuiteContractError(
                f"trusted oracle unexpectedly raised {type(exc).__name__}: {exc}"
            ) from exc
        if case.expected != oracle_value:
            raise SuiteContractError(
                f"case {index} expected {case.expected!r}; trusted outcome is {oracle_value!r}"
            )
    return suite
