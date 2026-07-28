# 本地环境变量与快捷运行

日期：2026-07-27  
状态：已实现

## 目的

避免每次打开 PowerShell 都手动设置 API Key，同时确保 Key 不进入 Git。

## 文件

- `.env`：本机私密配置，已被 `.gitignore` 排除。
- `scripts/load-env.ps1`：只向当前脚本进程加载配置。
- `scripts/run-agentloop.ps1`：加载配置并运行正式 CLI。
- `scripts/run-benchmark.ps1`：加载配置并运行 Benchmark。

## 安全注意

- `.env` 是本地明文文件，不要截图、发送或提交。
- 不要把真实 Key 写入 `.env.example`。
- 脚本不会打印 API Key。

