from agentloop import main_v2


def test_v2_dispatches_direct(monkeypatch) -> None:
    captured = {}

    def fake_main(args):
        captured["args"] = args
        return 7

    monkeypatch.setitem(main_v2.COMMANDS, "direct", fake_main)

    result = main_v2.main(["direct", "--model", "gpt-test"])

    assert result == 7
    assert captured["args"] == ["--model", "gpt-test"]


def test_v2_dispatches_adaptive(monkeypatch) -> None:
    captured = {}

    def fake_main(args):
        captured["args"] = args
        return 0

    monkeypatch.setitem(main_v2.COMMANDS, "adaptive", fake_main)

    result = main_v2.main(["adaptive", "--request-timeout", "30"])

    assert result == 0
    assert captured["args"] == ["--request-timeout", "30"]
