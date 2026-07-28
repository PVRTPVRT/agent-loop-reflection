# 正式 CLI 验证结果

日期：2026-07-27  
状态：已验证

## 结果

- Ruff：全部通过。
- Pytest：22 项测试通过。
- `python -m agentloop --help` 正常显示参数说明。
- 缺少 `OPENAI_API_KEY` 时返回退出码 2，并在网络请求前输出配置错误。
- 人类可读输出与 JSON 输出均通过 Stub Workflow 测试。

## 正式入口

```powershell
.\.venv\Scripts\python.exe -m agentloop `
  "实现 Python 函数 add(a, b)" `
  --task-id add-demo
```

## 下一步

建立版本化 benchmark 数据集、Direct 与 Reflection 两种策略，以及统一实验结果指标。

