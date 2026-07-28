"""Deterministically normalize model-generated suites using public contracts."""

from __future__ import annotations

from dataclasses import dataclass

from agentloop.contracts_v2 import TaskContractV2
from agentloop.evaluation_v2_models import EvaluationCase, EvaluationSuite
from agentloop.oracles import ORACLES
from agentloop.suite_validation import (
    SuiteContractError,
    _matching_exception,
    _validate_parameter,
    validate_suite,
)


@dataclass(frozen=True, slots=True)
class NormalizedSuite:
    suite: EvaluationSuite
    corrections: tuple[str, ...]


def normalize_suite(
    suite: EvaluationSuite,
    contract: TaskContractV2,
) -> NormalizedSuite:
    if suite.function_name != contract.function_name:
        raise SuiteContractError(f"function_name must be {contract.function_name!r}")
    oracle = ORACLES.get(contract.oracle)
    if oracle is None:
        raise SuiteContractError(f"Unknown trusted oracle {contract.oracle!r}")

    normalized_cases = []
    corrections = []
    for index, case in enumerate(suite.test_cases, 1):
        if len(case.args) != len(contract.parameters):
            corrections.append(f"dropped case {index}: invalid argument count")
            continue
        args_by_name = {}
        try:
            for value, parameter in zip(case.args, contract.parameters, strict=True):
                _validate_parameter(value, parameter)
                args_by_name[parameter.name] = value
        except SuiteContractError as exc:
            corrections.append(f"dropped case {index}: {exc}")
            continue

        required_exception = _matching_exception(args_by_name, contract.exceptions)
        if required_exception is not None:
            expected = None
        else:
            expected = oracle(*case.args)

        if case.expected != expected or case.expected_exception != required_exception:
            corrections.append(
                f"corrected case {index} outcome from "
                f"({case.expected!r}, {case.expected_exception!r}) to "
                f"({expected!r}, {required_exception!r})"
            )
        normalized_cases.append(
            EvaluationCase(
                args=case.args,
                expected=expected,
                expected_exception=required_exception,
                description=case.description,
            )
        )

    if not normalized_cases:
        raise SuiteContractError("all generated cases were outside the public contract")
    normalized = EvaluationSuite(
        function_name=suite.function_name,
        test_cases=normalized_cases,
    )
    validate_suite(normalized, contract)
    return NormalizedSuite(
        suite=normalized,
        corrections=tuple(corrections),
    )
