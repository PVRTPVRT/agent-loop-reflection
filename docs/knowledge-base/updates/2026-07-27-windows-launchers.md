# Windows CMD 启动器

本机 PowerShell Execution Policy 禁止直接运行 `.ps1`。项目增加 `.cmd` 包装器，
仅为当前进程传入 `-ExecutionPolicy Bypass`，不会修改系统或用户级执行策略。

推荐入口：

```powershell
.\scripts\run-agentloop.cmd "实现 add(a, b)"
.\scripts\run-benchmark.cmd --strategy both --limit 2
```

