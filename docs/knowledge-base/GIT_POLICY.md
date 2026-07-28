# Git 提交策略

## 应提交

- `src/`
- `tests/`，但后续删除 legacy 沙箱测试
- `scripts/run-v2.cmd`
- `scripts/test-v2-managed.cmd`
- `benchmarks/datasets/`
- `benchmarks/contracts/`
- `benchmarks/routing/`
- 三次 Direct 与三次 Lean Reflection 正式结果
- Adaptive 正式结果
- `docs/knowledge-base/`
- `pyproject.toml`、`.coveragerc`、`.env.example`

## 默认不提交

- `.env`
- `.venv/`
- `__pycache__/`
- `.pytest_cache/`
- 临时 smoke、失败和过渡实验结果
- 大部分 `benchmarks/traces/`
- Docker 临时文件

## 可提交的示例 Trace

为了展示可观测性，可以只提交：

- Adaptive `add-001` Direct 路径；
- 一条 Oracle 有修正记录的 deduplicate trace；
- 一条包含 `expected_exception` 的 factorial trace。

## 首次提交前阻塞项

1. 用 `README_V2.md` 替换旧 `README.md`。
2. 更新 `.gitignore`，忽略原始 traces 与非精选 results。
3. 删除或归档 legacy CLI、旧沙箱和阶段性测试。
4. 确认 `git diff --cached` 不包含 `.env` 或 API Key。
