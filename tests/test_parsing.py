import pytest

from agentloop.parsing import (
    ModelOutputError,
    extract_python_code,
    parse_test_suite,
)


def test_parse_fenced_test_suite() -> None:
    suite = parse_test_suite(
        """```json
        {
          "function_name": "add",
          "test_cases": [
            {"args": [1, 2], "expected": 3, "description": "normal"}
          ]
        }
        ```"""
    )
    assert suite.function_name == "add"
    assert suite.test_cases[0].expected == 3


def test_invalid_json_raises_contract_error() -> None:
    with pytest.raises(ModelOutputError, match="合法 JSON"):
        parse_test_suite("not json")


def test_extract_python_code_checks_syntax() -> None:
    assert extract_python_code("```python\ndef add(a, b):\n    return a + b\n```").startswith(
        "def add"
    )
    with pytest.raises(ModelOutputError, match="语法错误"):
        extract_python_code("def broken(:")
