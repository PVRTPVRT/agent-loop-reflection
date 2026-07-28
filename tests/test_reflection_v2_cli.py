from agentloop.reflection_v2_cli import build_parser


def test_reflection_v2_cli_supports_targeted_tasks_and_budgets() -> None:
    args = build_parser().parse_args(
        [
            "--task-id",
            "factorial-001",
            "--request-timeout",
            "20",
            "--max-retries",
            "0",
        ]
    )

    assert args.task_id == ["factorial-001"]
    assert args.request_timeout == 20
    assert args.max_retries == 0
