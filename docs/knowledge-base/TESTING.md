# 正式测试策略

## 推荐命令

```powershell
.\scripts\test-v2-managed.cmd
```

该命令：

1. 运行 Ruff；
2. 运行 130 项不依赖 Docker 的确定性测试；
3. 单独运行 8 项函数、仓库与 Managed 清理 Docker 测试；
4. 不调用 OpenAI API。

## 测试分层

常规阶段显式排除所有需要 Docker 的测试，避免同一测试在常规阶段和 Docker
阶段重复执行。Docker 阶段运行：

- `tests/test_managed_sandbox_v2.py`
- `tests/test_docker_v2_integration.py`
- `tests/test_repository_docker_integration_v0_4.py`，其中版本化 Mutation Matrix 会验证
  Calculator 与 Frame Decoder 的 4 个 repair/non-fix 对照 Patch

旧未跟踪的 `scripts/test-v2.cmd` 不属于发布门禁。旧 `docker run --rm` 执行路径及
其专属测试已经删除；`sandbox.py` 只准备 Docker runtime，`sandbox_v2.py` 只构建
函数 harness，所有执行统一由 Managed 命名容器生命周期负责。

## 当前门槛

- Ruff 必须通过；
- 130 项确定性测试必须全部通过；
- 8 项 Docker 集成测试必须全部通过；
- Managed Docker 成功路径必须清理容器；
- Managed Docker 超时路径必须清理容器；
- 提交的 `repository-v0.4` 报告指纹必须与数据集一致，4/4 Mutation 必须匹配预期；
- 默认沙箱镜像必须使用不可变 OCI digest；
- 测试结束后不得出现名称匹配 `agentloop-[0-9a-f]{12}` 的执行容器；Phoenix
  服务容器不计入该规则。
