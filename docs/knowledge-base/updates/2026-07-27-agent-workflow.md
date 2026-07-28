# Agent 工作流模块化迁移

日期：2026-07-27  
状态：待验证

## 新模块

- `parsing.py`：集中处理 JSON 测试套件和 Python 代码输出契约。
- `agents.py`：Tester、Critic、Coder，全部依赖 `LLMProvider`。
- `verifier.py`：定义 Verifier Protocol，并适配安全 Docker 执行层。
- `workflow.py`：显式编排辩论轮次、编码轮次、反馈和终止条件。

## 设计原则

- Agent 不直接依赖 OpenAI SDK。
- Workflow 不直接依赖 Docker。
- 每轮关键行为写入 `AgentEvent`，为后续 Trace 和可视化保留结构化数据。
- 辩论轮数和编码轮数均有硬上限。
- 模型输出在进入业务逻辑前完成 JSON、Pydantic 或 AST 校验。

## 离线验收场景

1. Tester 生成套件，Critic 直接批准。
2. Coder 首轮失败，接收 Verifier 反馈后第二轮修复成功。
3. Critic 拒绝首版套件，Tester 修订后再次通过。

