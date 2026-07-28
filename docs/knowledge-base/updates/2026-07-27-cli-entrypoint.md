# 配置层与正式 CLI

日期：2026-07-27  
状态：待验证

## 变更

- 新增 `AppSettings`，统一读取 API Key、模型和工作流轮次限制。
- 新增 composition root，集中装配 Provider、Agent、Verifier 和 Workflow。
- 新增 `python -m agentloop` 正式入口。
- 支持人类可读输出和完整 JSON 输出。
- 新增 `.env.example`，真实 Key 不进入仓库。
- 新增面向项目使用者的根 README。

## 安全边界

- CLI 不接受命令行 API Key，避免凭据进入 Shell 历史或进程列表。
- 未设置 `OPENAI_API_KEY` 时在调用模型前失败。
- CLI 测试使用 Stub Workflow，不会发送真实 API 请求。

