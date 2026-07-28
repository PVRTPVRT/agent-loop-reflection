# Agent Loop Reflection V2

[![CI](https://github.com/PVRTPVRT/agent-loop-reflection/actions/workflows/ci.yml/badge.svg)](https://github.com/PVRTPVRT/agent-loop-reflection/actions/workflows/ci.yml)

一个可评测、可观测、成本感知的 Coding Agent 系统。v0.2 将 Adaptive 的失败分支
升级为 Evidence-Driven Repair：Direct 失败后保留候选代码、冻结路由套件和
expected/actual 证据，针对现有候选完成诊断、修复和双重验收。

## v0.2 闭环

```text
Direct candidate
  -> public routing suite in Managed Docker
     -> pass: independent hidden evaluation
     -> fail: RepairContext(candidate + suite + failure evidence)
        -> Critic diagnoses current candidate
        -> Coder patches current candidate
        -> frozen routing suite (bounded retries)
        -> independent hidden evaluation

success = internal route acceptance AND hidden acceptance
```

## 核心能力

- Direct、Lean Reflection、Adaptive 与 Recorded Failure Replay
- OpenAI Responses API、Structured Outputs 和角色级调用预算
- Pydantic V2 不可变数据契约与 `expected_exception`
- 公开任务契约、可信 Oracle 与版本化 Benchmark
- Evidence-Driven Repair：失败候选和真实验证证据跨工作流传递
- Managed Docker：非 root、只读文件系统、无网络、资源限制、强制清理
- API 超时、失败隔离、增量检查点、Token/延迟和逐 Agent Trace
- 合取成功门控：内部修复失败不能被覆盖不足的隐藏集判为最终成功

## 安装

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

复制 `.env.example` 为 `.env`，写入本地 `OPENAI_API_KEY`。`.env` 已被 Git
忽略。

## 运行

常规策略：

```powershell
.\scripts\run-v2.cmd direct
.\scripts\run-v2.cmd reflection
.\scripts\run-v2.cmd adaptive
```

v0.2 单题自然 Adaptive 与明确标注的故障重放：

```powershell
.\scripts\run-v0.2-repair-pilot-r2.cmd
.\scripts\run-v0.2-repair-replay.cmd
```

`repair-replay` 先证明记录候选确实失败，再调用真实 Critic/Coder 修复；它与自然
Adaptive 使用不同实验标签，不计入自然失败率或自然通过率。

## 测试

```powershell
.\scripts\test-v2-managed.cmd
```

该命令不会调用 OpenAI API。当前完整回归为 84 项常规测试和 2 项 Docker
集成测试。

## 已验证结果

### v0.2 闭环试验

| Experiment | Path | Result | Calls | Tokens | Duration |
|---|---|---:|---:|---:|---:|
| R2 natural Adaptive | Direct | 1/1 | 1 | 751 | 6.98 s |
| R2 recorded failure replay | Repair | 1/1 | 2 | 3,813 | 14.84 s |

Repair Replay 从 R1 真实产生且可在 Docker 中复现的 TTL/LRU 失败候选开始，一轮
修复后通过 2/2 公开路由用例和 6/6 独立 R2 隐藏用例。

R1 同时暴露过一次假阳性：内部 Repair 失败，但旧隐藏集盲点导致最终结果被错误
标记为成功。v0.2 保留该事故数据，并增加合取门控和防回归测试。

### v0.1 基线

| Strategy | Result | Tokens/task | Duration/task |
|---|---:|---:|---:|
| Direct, 3×8 | 24/24 | 138.7 | 2.38 s |
| Lean Reflection, 3×8 | 18/24 | 2,486.2 | 49.43 s |
| Adaptive, 1×8 | 8/8 | 152.4 | 3.32 s |

这些小型任务结果用于成本与可靠性基线，不代表 Reflection 在广泛任务上统计优于
Direct。v0.2 的 TTL/LRU 仍是单个困难状态机试验，也不宣称跨领域泛化。

## Python API

```python
from agentloop.v2 import (
    AdaptiveStrategyV2,
    EvidenceDrivenRepairWorkflow,
    ManagedDockerSandboxV2,
    RepairContext,
    RepairReplayStrategyV2,
)
```

## 文档

- [作品展示：架构与结果](docs/portfolio-showcase.md)
- [Evidence-Driven Repair 架构](docs/knowledge-base/architecture/evidence-driven-repair.md)
- [v0.2 闭环实验与 R1 假阳性复盘](docs/knowledge-base/experiments/2026-07-28-v0.2-repair-closed-loop.md)
- [ADR-002：合取成功门控](docs/knowledge-base/decisions/ADR-002-conjunctive-success-gate.md)
- [安全执行决策](docs/knowledge-base/decisions/ADR-001-secure-execution.md)
- [测试说明](docs/knowledge-base/TESTING.md)
- [v0.1 重复实验](docs/knowledge-base/experiments/2026-07-27-v2-repeated-results.md)
