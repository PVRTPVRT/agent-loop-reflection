# 类型化模型与 LLM Provider 实施记录

日期：2026-07-27  
状态：待验证

## 目标

解除 Agent 逻辑与 OpenAI SDK 的直接耦合，使工作流可以：

- 使用 Fake LLM 进行零 API 成本测试。
- 在不改业务代码的情况下替换模型或 Provider。
- 统一记录 Token 使用量，为后续成本实验打基础。
- 在模块边界校验任务、测试用例和模型响应。

## 实现

- `models.py`：CodingTask、TestSuite、LLMRequest、LLMResponse、TokenUsage 等模型。
- `llm.py`：LLMProvider Protocol、OpenAI Responses API Provider、Fake Provider。
- OpenAI 模型通过 `OPENAI_MODEL` 配置，默认使用适合批量评测的
  `gpt-5.6-luna`。
- OpenAI 请求设置 `store=False`，不依赖服务端会话状态。

## 文档依据

OpenAI 当前模型指南建议 Agent 和多轮工作流使用 Responses API。模型保持可配置，
实际选择必须通过项目自己的质量、成本和延迟评测确定。

## 验证

本步骤不调用真实 OpenAI API。所有 Provider 测试使用 Stub 或 Fake 对象。

