# GPT-5.4 Nano Reflection 兼容性结论

日期：2026-07-27

## 尝试

针对 coding-v1 的首个任务，分别测试：

1. 默认 Provider。
2. `reasoning=low`，最小输出预算 4,000 Token。
3. `reasoning=none`，最小输出预算 4,000 Token。

三种配置下，Tester 都连续 3 次未产生可解析 JSON，工作流在进入 Coder 前终止。

## 结论

- Nano 的 Direct 代码生成可以移植：2/2 通过。
- Nano 的 Reflection 结构化 Tester 暂不可移植。
- 继续增加 Prompt 重试只会浪费 Token，不应作为修复方案。
- 下一实现应使用 Responses API Structured Outputs / JSON Schema。
- BenchmarkRunner 必须增加单任务异常隔离和增量保存，避免失败时丢失已完成结果。

## 成本策略

在 Structured Outputs 完成前：

- Nano 仅用于 Direct。
- Luna 用于 Reflection 小样本。
- 不运行完整 Nano Reflection 数据集。

