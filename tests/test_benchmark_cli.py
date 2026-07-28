from agentloop.benchmark_cli import main
from agentloop.benchmark_models import (
    AggregateMetrics,
    BenchmarkReport,
)


def test_benchmark_cli_rejects_invalid_limit(capsys) -> None:
    exit_code = main(["--limit", "0"])

    output = capsys.readouterr()
    assert exit_code == 2
    assert "--limit 必须大于 0" in output.err


def test_benchmark_cli_requires_api_key(monkeypatch, capsys) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = main(["--limit", "1"])

    output = capsys.readouterr()
    assert exit_code == 2
    assert "OPENAI_API_KEY" in output.err


def test_benchmark_cli_writes_report_without_calling_api(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    report = BenchmarkReport(
        dataset_id="coding-v1",
        dataset_fingerprint="abc123",
        created_at="2026-07-27T00:00:00+00:00",
        results=[],
        aggregates=[
            AggregateMetrics(
                strategy="direct",
                total_tasks=1,
                passed_tasks=1,
                pass_rate=1,
                average_duration_ms=10,
                average_model_calls=1,
                average_total_tokens=20,
                average_coding_rounds=1,
            )
        ],
    )
    monkeypatch.setattr(
        "agentloop.benchmark_cli.BenchmarkRunner.run",
        lambda self, dataset, strategies, limit=None: report,
    )
    output_path = tmp_path / "report.json"

    exit_code = main(
        [
            "--strategy",
            "direct",
            "--limit",
            "1",
            "--output",
            str(output_path),
        ]
    )

    output = capsys.readouterr()
    assert exit_code == 0
    assert "direct: 1/1 (100.0%)" in output.out
    assert output_path.exists()
    assert '"dataset_id": "coding-v1"' in output_path.read_text(encoding="utf-8")
