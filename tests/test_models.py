import pytest
from pydantic import ValidationError

from agentloop.models import CodingTask, TestCase, TestSuite


def test_coding_task_rejects_empty_prompt() -> None:
    with pytest.raises(ValidationError):
        CodingTask(task_id="task-1", prompt="")


def test_test_suite_rejects_duplicate_cases() -> None:
    duplicate = TestCase(args=[1], expected=1)
    with pytest.raises(ValidationError, match="duplicates"):
        TestSuite(
            function_name="identity",
            test_cases=[duplicate, duplicate],
        )


def test_domain_models_are_immutable() -> None:
    task = CodingTask(task_id="task-1", prompt="Implement add")
    with pytest.raises(ValidationError):
        task.prompt = "changed"
