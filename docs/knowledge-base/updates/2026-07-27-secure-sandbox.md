# 安全执行层实施记录

日期：2026-07-27  
状态：已验证

## 变更

- 新增 `src/agentloop/sandbox.py`，作为后续架构唯一允许使用的代码执行层。
- Docker 不可用时抛出 `SandboxUnavailableError`，不提供自动宿主机回退。
- 容器采用禁网、只读根文件系统、只读代码卷、非 root 用户运行。
- 清空 Linux capabilities，并启用 `no-new-privileges`。
- 增加 CPU、内存、PID、临时目录和宿主机执行时间限制。
- 新增 `pyproject.toml`、pytest、覆盖率工具和 Ruff 配置。
- `demo.py` 标记为 legacy 原型，工作流迁移完成前保留，但不作为新架构入口。

## 验证结果

以下场景已通过自动测试：

1. 正常 Python 函数能够在 Docker 中通过测试。
2. 向容器根文件系统写入文件被拒绝。
3. 无限循环被宿主机超时终止。
4. Docker 命令包含预期安全参数。
5. Docker 不可用时执行层 fail closed。

验证命令：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests
```

验证结果：`5 passed`。

## 下一步

定义 Pydantic 领域模型与 LLM Provider 接口，把 Tester、Critic、Coder 和工作流逐步迁移出
`demo.py`，并用 Fake LLM 建立不消耗 API 的单元测试。

