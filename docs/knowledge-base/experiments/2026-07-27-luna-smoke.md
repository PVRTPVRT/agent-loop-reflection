# GPT-5.6 Luna 小规模策略对照

日期：2026-07-27  
数据集：coding-v1  
数据集指纹：`305532a189ed22e9`  
样本：前 2 个任务  
模型：gpt-5.6-luna

## 结果

| 策略 | 通过率 | 平均调用 | 平均 Token | 平均耗时 |
|---|---:|---:|---:|---:|
| Direct | 2/2（100%） | 1.0 | 160 | 3.29 秒 |
| Reflection | 2/2（100%） | 5.5 | 5,241 | 30.98 秒 |

## 逐任务估算费用

按标准短上下文价格：输入 `$1 / 1M tokens`、输出 `$6 / 1M tokens`。

| 策略 | 任务 | 估算费用 |
|---|---|---:|
| Direct | add-001 | $0.000281 |
| Direct | factorial-001 | $0.000979 |
| Reflection | add-001 | $0.035512 |
| Reflection | factorial-001 | $0.006480 |

本次总估算费用：`$0.043252`。

## 初步结论

- 在两个简单任务上，两种策略都达到 100%，Reflection 暂未表现出质量收益。
- Reflection 平均 Token 约为 Direct 的 32.8 倍，平均延迟约为 9.4 倍。
- `add-001` 的 Reflection 使用 7 次调用和 2 轮辩论/编码，存在明显过度反思。
- 后续重点不应盲目增加反思，而应实现条件触发与提前停止。
- 样本量只有 2，不能据此宣称整体质量差异。

## 原始结果

- `benchmarks/results/direct-smoke.json`
- `benchmarks/results/comparison-smoke.json`

