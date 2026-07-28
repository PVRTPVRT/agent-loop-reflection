# Benchmark v1 与策略对照实验

日期：2026-07-27  
状态：待验证

## 数据集

`benchmarks/datasets/coding-v1.json`：

- Schema 版本：1.0
- 数据集 ID：coding-v1
- 任务数：8
- 类别：算术、序列、字符串、边界、集合
- 难度：easy / medium
- 每个任务包含独立最终验收套件
- 数据集内容生成 SHA-256 短指纹，结果可关联到精确版本

## 公平性设计

- Direct 只看到任务描述和目标函数名。
- Reflection 可以自行生成内部测试并进行反思。
- 两种策略最终都由相同的独立 Benchmark 套件评分。
- Reflection 的“内部成功”与“Benchmark 成功”分别记录，防止测试自洽却答案错误。

## 指标

- Benchmark 通过率
- 单任务耗时
- 模型调用次数
- 输入、输出和总 Token
- 编码轮次
- 辩论轮次
- 失败消息和最终代码

## 运行

```powershell
.\.venv\Scripts\python.exe -m agentloop.benchmark_cli `
  --dataset benchmarks/datasets/coding-v1.json `
  --strategy both `
  --output benchmarks/results/coding-v1.json
```

真实运行会调用 OpenAI API 并产生费用。建议先用 `--limit 2` 做小样本检查。

