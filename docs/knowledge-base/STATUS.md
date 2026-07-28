# 当前正式状态

## 正式产品路径

| 模式 | 入口 | 用途 |
| --- | --- | --- |
| Direct V2 | `run-v2.cmd direct` | 最低成本基线 |
| Lean Reflection V2 | `run-v2.cmd reflection` | 固定三角色反思 |
| Adaptive V2 | `run-v2.cmd adaptive` | 默认推荐路径 |

Adaptive V2 是项目主路径。其他 portability、strict、observable、
contract 和 comparison 入口属于演进实验，暂时保留用于复现实验，不作为用户入口。

## 正式基础设施

- `EvaluationDataset` / `EvaluationSuite` V2
- `expected_exception`
- `ContractRegistryV2`
- trusted local Oracles
- deterministic suite normalization
- `ManagedDockerSandboxV2`
- bounded API timeout and retry policy
- incremental checkpoints and per-task traces
- independent public routing suites

## 当前验证

- Ruff：通过
- pytest：74 项收集
- 安全回归：73 项通过，1 项旧沙箱测试排除
- 总覆盖率：68%
- Adaptive 核心策略：100%
- Adaptive 真实实验：8/8

## 已弃用但尚未删除

- V1 Benchmark 和 TestSuite
- `docker run --rm` 旧沙箱路径
- 多个阶段性 portability/comparison CLI
- 根目录 `demo.py`

删除前需要先把历史实验复现说明与正式代码彻底分离。
