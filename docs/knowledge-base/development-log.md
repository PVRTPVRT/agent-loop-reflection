# Agent Loop Reflection 进程开发日志

> 本日志记录项目从单文件原型到自适应 Coding Agent 评测系统的完整演进。
> 日期以本地时区 Asia/Shanghai 为准。只记录已经实现、运行或验证的事实。

## 2026-07-27：环境与项目基线

### 目标

将原始 `demo.py` 改造成可测试、可评测、可在简历中展示的工程项目。

### 完成

- 验证 Python 3.12.10、Git 2.55、WSL 2.7.11。
- 更新 WSL，启动 Docker Desktop 29.6.2。
- 建立 `.venv`、`pyproject.toml`、pytest、Ruff 和项目知识库。
- 建立 `.env` 本地配置与 Windows `.cmd` 启动器。

### 遇到的问题

- `wsl.exe --update` 因网络策略返回 403。
- 改用 `winget install Microsoft.WSL` 安装 WSL 2.7.11。
- PowerShell 临时环境变量每次新开窗口都会丢失。

### 解决

- 使用被 `.gitignore` 排除的 `.env` 保存本地 Key。
- Windows 启动器自动读取 `.env`，不再要求每次手动设置变量。

## 2026-07-27：模块化与类型化

### 完成

- 将单文件原型拆为模型、Provider、Agent、Workflow、Verifier、CLI 和 Benchmark。
- 使用 Pydantic 定义不可变跨模块契约。
- 定义统一 `LLMProvider`，使 OpenAI 与 Fake Provider 可替换。
- 建立无需 API 的离线测试。

### 价值

- Agent 之间不再传递无约束字典。
- 工作流、解析器、Provider 和评测可以独立测试。
- 真实模型调用与离线开发解耦。

## 2026-07-27：Docker 安全执行

### 完成

- 生成代码只在 Docker 中执行。
- 禁止网络、只读根目录、删除 capabilities。
- 限制 CPU、内存、PID、用户权限和执行时间。
- Docker 不可用时失败关闭，不回退到宿主机执行。

### 遇到的问题

Windows 上 `docker run --rm` 的客户端进程被超时终止后，后台容器可能继续运行。
开发过程中曾精确识别并清理 22 个挂载 `agentloop_sandbox_*` 临时目录的容器。

### 解决

实现 `ManagedDockerSandboxV2`：

```text
docker create --name agentloop-...
    -> docker start
    -> docker wait
    -> docker logs
    -> finally docker rm -f
```

成功、失败、死循环、超时和中断路径均有清理测试。

## 2026-07-27：Reflection 工作流

### 初始流程

```text
Tester -> Critic -> Tester revision
                    |
                    v
                  Coder -> Verifier -> code repair
```

### 完成

- Tester 生成 JSON 测试。
- Critic 检查覆盖率与需求一致性。
- Coder 根据测试与 Verifier 反馈生成或修复代码。
- 限制讨论轮数、编码轮数和解析重试，防止无限循环。
- 记录结构化 AgentEvent。

## 2026-07-27：版本化 Benchmark

### 完成

- 建立固定任务 ID、难度、类别和隐藏评测套件。
- 使用数据集指纹保证实验可追溯。
- Direct 与 Reflection 使用相同隐藏评测。
- 记录调用次数、Token、耗时、内部结果和外部结果。
- 单任务失败隔离，逐任务保存检查点。

## 2026-07-27：低成本模型可移植性

### 初始结果

- Luna Direct 冒烟测试成功。
- Luna Reflection 成本和 Token 明显高于 Direct。
- GPT-5.4 nano Direct 成功。
- GPT-5.4 nano Reflection 的 Tester 多次返回空或无效 JSON。

### 解决

使用 OpenAI Responses API Structured Outputs 和严格 JSON Schema。

第一版 Schema 使用无类型 `{}`，API 返回 400：

```text
schema must have a 'type' key
```

随后将动态 JSON 值改为显式 `anyOf` 类型联合，nano Reflection 成功。

## 2026-07-27：可观测性与需求约束

### 发现

一次 `add` 实验出现：

```text
internal_success = false
hidden_benchmark = true
```

生成代码包含题目未要求的 `inf` 字符串转换和类型检查。

### 根因

- Tester 擅自扩展任务要求。
- 报告没有保存内部套件和每轮 Verifier 信息。

### 解决

- 保存完整逐任务 trace。
- Tester 禁止引入未声明类型、异常和返回格式。
- Critic 增加“是否超出原始需求”的审查。
- 将内部成功和隐藏 Benchmark 成功分开记录。

## 2026-07-27：公开任务契约

### 问题

Tester 将“数字”理解为整数和浮点数，Critic 却认为浮点数超出需求。

### 解决

为每个任务建立公开契约：

- 函数名；
- 参数名称与输入域；
- 返回行为；
- 明确异常。

公开契约不包含隐藏测试具体值。Tester 与 Critic 使用相同契约。

结果：`add` 成功路径从 6 次调用、7,183 tokens 降为 3 次调用、
1,917 tokens。

## 2026-07-27：V2 测试 Schema

### 问题

V1 只能表示 `expected`，无法区分“返回 None”和“应抛 ValueError”。

### 解决

V2 每个用例包含：

```json
{
  "args": [-1],
  "expected": null,
  "expected_exception": "ValueError"
}
```

Docker Harness 能验证：

- 正确异常；
- 错误异常类型；
- 应抛异常但正常返回；
- 不应抛异常却抛出。

隐藏评测加入 factorial、fibonacci 负数以及 clamp 非法区间。

## 2026-07-27：可信 Oracle 与规范化

### 发现

格式正确的模型测试仍可能在语义上错误：

- 使用字符串占位符表示 `100!`；
- 给 deduplicate 输入不可哈希嵌套列表；
- 错误处理 `1 == True`、`0 == False`。

### 解决

实现 8 个本地可信 Oracle。模型生成测试后执行：

```text
Pydantic Schema
    -> public contract domain validation
    -> trusted Oracle expected calculation
    -> correct expected/expected_exception
    -> drop out-of-contract cases
```

Oracle 不进入模型提示，也不泄漏隐藏测试。

在 18 条成功 Reflection trace 中，共修正或删除 41 个错误生成结果。

## 2026-07-27：Lean Reflection

### 问题

Critic 会要求契约外或低价值测试，导致套件膨胀和第二轮讨论。

### 解决

- 机器契约和 Oracle 成为正确性硬门。
- Critic 只做一次建议性覆盖审查。
- Tester、Critic、Coder 分别使用 4000、500、2000 输出预算。
- 标准成功路径固定为 Tester -> Critic -> Coder。

deduplicate 从 5 次调用、7,967 tokens 降到 3 次调用、2,755 tokens。

## 2026-07-27 至 2026-07-28：重复实验

### 协议

- 8 个 V2 任务；
- Direct 与 Lean Reflection；
- 每个策略独立运行 3 次；
- 每个策略 24 个任务观察值；
- GPT-5.4 nano，reasoning `none`；
- 60 秒请求 SLO，SDK 自动重试为 0。

### 结果

| Strategy | Pass | Timeouts | Tokens/task | Duration/task | Cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| Direct | 24/24 | 0 | 138.7 | 2.38 s | $0.0022637 |
| Lean Reflection | 18/24 | 6 | 2,486.2 | 49.43 s | $0.03249805 |

Reflection 的 6 次失败均为 API 超时。成功完成的 18 次内部与隐藏评测均通过。

结论：多调用工作流会放大服务和网络超时风险；简单任务不应始终启用 Reflection。

## 2026-07-28：Adaptive 自适应路由

### 架构

```text
Direct
  -> public routing suite
     -> pass: hidden benchmark
     -> fail: Lean Reflection -> hidden benchmark
```

公开路由套件与隐藏评测分开存储，并有测试保证具体参数不重合。

### 真实结果

- 8/8 路由测试通过；
- 8/8 隐藏 Benchmark 通过；
- Direct 路径 8，Reflection 回退 0；
- 1 次调用/题；
- 152 tokens/题；
- 3.32 秒/题；
- 总估算费用 `$0.00089165`。

真实任务没有人为破坏 Direct 输出。Reflection 回退分支由确定性离线测试覆盖。

## 2026-07-28：当前健康状态

- Ruff：通过。
- pytest 收集：74 项。
- 安全回归：73 项通过，1 项旧沙箱集成测试暂时排除。
- 总覆盖率：68%。
- `AdaptiveStrategyV2`：100% 覆盖。
- Docker Desktop：29.6.2。
- Managed V2 路径无容器残留。

## 当前已知技术债

1. README 仍描述旧工作流和旧环境变量方式。
2. V1、过渡实验模块和正式 V2 模块同时存在，入口过多。
3. 旧 `docker run --rm` 沙箱测试在 Windows 中断时可能遗留容器。
4. 整体覆盖率受大量历史 CLI 和过渡模块影响，当前为 68%。
5. 仓库尚无 Git 基线提交，所有项目文件仍显示为未跟踪。
6. Adaptive 真实实验尚未在自然困难任务上触发 Reflection 回退。

## 下一阶段

1. 只保留 Direct V2、Lean Reflection V2、Adaptive V2 为正式入口。
2. 将 Managed Docker 下沉为唯一沙箱实现。
3. 更新 README、知识库索引和正式命令。
4. 清理或归档过渡模块和过期实验入口。
5. 将正式模块覆盖率提升到 80% 以上。
6. 建立 Git 首次提交与 GitHub Actions CI。
7. 增加困难任务，自然触发 Adaptive Reflection 回退。
8. 生成实验图表与项目展示页面。
