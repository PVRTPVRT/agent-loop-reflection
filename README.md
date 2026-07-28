# Agent Loop Reflection V2

[![CI](https://github.com/PVRTPVRT/agent-loop-reflection/actions/workflows/ci.yml/badge.svg)](https://github.com/PVRTPVRT/agent-loop-reflection/actions/workflows/ci.yml)

一个可评测、可观测、成本感知的 Coding Agent 系统，支持 Direct、Lean
Reflection 和 Adaptive 三种执行策略。

## 推荐流程

```text
Direct generation
    -> independent public routing suite in Managed Docker
       -> pass: return Direct result
       -> fail: run Lean Reflection
    -> hidden benchmark evaluation
```

## 核心能力

- OpenAI Responses API 与 Structured Outputs
- Pydantic V2 数据契约
- `expected_exception` 异常断言
- 机器可检查的公开任务契约
- 可信本地 Oracle 测试规范化
- Managed Docker 安全执行与强制清理
- API 超时、失败隔离和增量检查点
- Token、费用、延迟和逐 Agent Trace
- 版本化 Direct/Reflection/Adaptive 实验

## 安装

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

复制 `.env.example` 为 `.env`，写入本地 `OPENAI_API_KEY`。`.env` 已被
Git 忽略。

## 正式命令

```powershell
.\scripts\run-v2.cmd direct
.\scripts\run-v2.cmd reflection
.\scripts\run-v2.cmd adaptive
```

默认推荐 `adaptive`。

## 测试

```powershell
.\scripts\test-v2-managed.cmd
```

该命令不会调用 OpenAI API。

## 已验证结果

| Strategy | Result | Tokens/task | Duration/task |
| --- | ---: | ---: | ---: |
| Direct, 3×8 | 24/24 | 138.7 | 2.38 s |
| Lean Reflection, 3×8 | 18/24 | 2,486.2 | 49.43 s |
| Adaptive, 1×8 | 8/8 | 152.4 | 3.32 s |

Lean Reflection 的 6 次失败均为 API 超时；完成工作流的 18 次均通过内部和
隐藏评测。Adaptive 在简单任务上保留了 Direct 的成本和可靠性。

## Python API

正式公共 API 从 `agentloop.v2` 导入：

```python
from agentloop.v2 import (
    AdaptiveStrategyV2,
    EvaluationDataset,
    ManagedDockerSandboxV2,
)
```

## 文档

- [架构图与实验结果展示](docs/portfolio-showcase.md)
- [Adaptive 路由架构](docs/knowledge-base/architecture/adaptive-routing.md)
- [安全执行决策](docs/knowledge-base/decisions/ADR-001-secure-execution.md)
- [测试说明](docs/knowledge-base/TESTING.md)
- [正式实验协议](docs/knowledge-base/experiments/coding-v2-full-protocol.md)
- [重复实验结果](docs/knowledge-base/experiments/2026-07-27-v2-repeated-results.md)
- [Adaptive 实验](docs/knowledge-base/experiments/2026-07-28-adaptive-v2-result.md)
