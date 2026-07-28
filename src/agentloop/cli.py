"""Command-line interface for Agent Loop Reflection."""

from __future__ import annotations

import argparse
import sys
import uuid
from collections.abc import Sequence

from agentloop.app import build_workflow
from agentloop.config import AppSettings, ConfigurationError
from agentloop.models import CodingTask


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentloop",
        description="Run a typed, sandboxed coding-agent reflection workflow.",
    )
    parser.add_argument("task", help="自然语言编程任务")
    parser.add_argument("--task-id", help="可复现实验使用的任务 ID")
    parser.add_argument("--model", help="覆盖 OPENAI_MODEL")
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="以 JSON 输出完整结构化结果",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = AppSettings.from_env().with_model(args.model)
        workflow = build_workflow(settings)
        task = CodingTask(
            task_id=args.task_id or f"cli-{uuid.uuid4().hex[:12]}",
            prompt=args.task,
            category="cli",
        )
        result = workflow.run(task)
    except ConfigurationError as exc:
        print(f"配置错误：{exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("任务已取消。", file=sys.stderr)
        return 130

    if args.json_output:
        print(result.model_dump_json(indent=2))
    else:
        status = "成功" if result.success else "失败"
        print(f"[{status}] task_id={result.task_id}")
        print(f"辩论轮次={result.debate_rounds}，编码轮次={result.coding_rounds}")
        print(result.final_message)
        if result.code:
            print("\n生成代码：")
            print(result.code)
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
