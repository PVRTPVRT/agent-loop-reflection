import pytest
from pydantic import ValidationError

from agentloop.contracts_v2 import TaskContractV2


def contract_data(dynamic_exceptions):
    return {
        "function_name": "example",
        "oracle": "example",
        "parameters": [],
        "exceptions": [],
        "dynamic_exceptions": dynamic_exceptions,
    }


@pytest.mark.parametrize(
    "exceptions",
    [
        ["not an identifier"],
        ["Failure"],
        ["ValueError", "ValueError"],
    ],
)
def test_dynamic_exception_names_are_restricted(exceptions) -> None:
    with pytest.raises(ValidationError):
        TaskContractV2.model_validate(contract_data(exceptions))


def test_dynamic_exception_class_names_are_accepted() -> None:
    contract = TaskContractV2.model_validate(
        contract_data(["ValueError", "DomainException"])
    )

    assert contract.dynamic_exceptions == ["ValueError", "DomainException"]
