# 架构现状

更新日期：2026-08-01

## 当前定位

Agent Loop Reflection 是一个可评测、可观测、成本感知的 Coding Agent 修复系统。
正式入口支持 Direct、Lean Reflection 与 Adaptive；生成候选必须经过冻结的评测规格，
所有不可信代码只在 Managed Docker 中执行。

## 两种评测边界

```text
SourceCodeArtifact + FunctionCaseSpec
        -> generated runner
        -> Managed Docker

RepositoryPatchArtifact + TestCommandSpec
        -> trusted fixture + exact SHA-256 revision
        -> disposable verified copy
        -> validated git apply
        -> protected-test recheck
        -> Managed Docker
```

函数与仓库验证共用同一个命名容器生命周期：无网络、只读根文件系统、只读候选挂载、
非 root 用户、capability 清空、`no-new-privileges`、CPU/内存/PID 限制和强制清理。
Docker 不可用时安全失败，系统不存在宿主机 `exec()` 回退路径。

## Agent 修复闭环

```text
Task + public contract
        -> Direct candidate
        -> frozen routing verification
        -> pass: independent hidden verification
        -> fail: RepairContext(candidate + evidence + attempt history)
        -> Critic diagnosis -> Coder revision -> bounded recheck
```

最终成功采用合取门控：内部路由验证和独立隐藏验证必须同时成功。Recorded Failure
Replay 只用于重现已知故障分支，不计入自然通过率。

## 当前证据

- 版本化函数困难矩阵：Frame Decoder、Idempotent Ledger、TTL/LRU。
- 版本化仓库矩阵：Calculator 与 Frame Decoder，4 个 repair/non-fix Mutation 4/4
  符合预期，不调用 LLM API。
- 130 项确定性测试和 8 项 Docker 集成测试。
- OpenTelemetry/Phoenix 提供运行时 Trace；JSON Benchmark/Trace 保存实验事实。
- 生产源码模块均能从正式入口或公开 V2 API 到达。

## 明确边界

仓库矩阵证明验证器能安全地区分修复与表面改动，但尚未证明 LLM 能稳定生成仓库
Patch。真实仓库级 Direct/Adaptive 重复实验会产生 API 费用，应作为后续独立实验，
不能由当前零 API 结果外推。
