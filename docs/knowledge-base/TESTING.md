# 正式测试策略

## 推荐命令

```powershell
.\scripts\test-v2-managed.cmd
```

该命令：

1. 运行 Ruff；
2. 运行全部非 legacy 测试；
3. 单独运行 Managed Docker 成功与超时清理测试；
4. 不调用 OpenAI API。

## Legacy 排除

以下文件验证旧 `docker run --rm` 沙箱，会在 Windows Docker 客户端中断时
留下后台容器，因此不属于正式 V2 回归：

- `tests/test_sandbox.py`
- `tests/test_docker_v2_integration.py`

旧 `scripts/test-v2.cmd` 是过渡入口，不应再使用。待已有文件 ACL 允许修改后，
将删除旧测试与过渡脚本，并把 Managed 实现下沉为唯一沙箱。

## 当前门槛

- Ruff 必须通过；
- 非 legacy 测试必须全部通过；
- Managed Docker 成功路径必须清理容器；
- Managed Docker 超时路径必须清理容器；
- 测试结束后 `docker ps` 不得出现 `agentloop-*` 容器。
