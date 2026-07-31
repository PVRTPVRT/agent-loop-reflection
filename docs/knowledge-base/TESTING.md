# 正式测试策略

## 推荐命令

```powershell
.\scripts\test-v2-managed.cmd
```

该命令：

1. 运行 Ruff；
2. 运行 104 项不依赖 Docker 的确定性测试；
3. 单独运行 5 项 Docker 语义与 Managed 清理测试；
4. 不调用 OpenAI API。

## 测试分层

常规阶段显式排除所有需要 Docker 的测试，避免同一测试在常规阶段和 Docker
阶段重复执行。Docker 阶段运行：

- `tests/test_managed_sandbox_v2.py`
- `tests/test_docker_v2_integration.py`

旧 `tests/test_sandbox.py` 和未跟踪的 `scripts/test-v2.cmd` 不属于发布门禁。
当前仍保留三层沙箱实现；下一阶段仓库执行器会与函数执行器共用一个 Managed
容器生命周期，届时再删除旧层，避免先重写一次、随后又因仓库任务重复重写。

## 当前门槛

- Ruff 必须通过；
- 104 项确定性测试必须全部通过；
- 5 项 Docker 集成测试必须全部通过；
- Managed Docker 成功路径必须清理容器；
- Managed Docker 超时路径必须清理容器；
- 测试结束后 `docker ps` 不得出现 `agentloop-*` 容器。
