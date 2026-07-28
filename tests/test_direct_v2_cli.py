from agentloop.direct_v2_cli import build_parser


def test_direct_v2_defaults_to_full_dataset() -> None:
    args = build_parser().parse_args([])

    assert args.dataset.name == "coding-v2-full.json"
    assert args.request_timeout == 60
    assert args.max_retries == 0
