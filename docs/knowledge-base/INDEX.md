# Agent Loop Reflection V2 知识库索引

这是当前正式索引。旧 `README.md` 保留早期历史信息，待 Windows ACL
允许已有文件补丁后替换。

## 当前事实

- [完整进程开发日志](development-log.md)
- [当前正式状态](STATUS.md)
- [简历项目要点](resume-project-points.md)

## 正式架构

- [V2 评测架构](architecture/v2-evaluation.md)
- [Lean Reflection](architecture/lean-reflection.md)
- [Adaptive 路由](architecture/adaptive-routing.md)
- [实验就绪状态](architecture/experiment-readiness.md)

## 核心实验

- [Direct vs Reflection 先导实验](experiments/2026-07-27-direct-vs-reflection-pilot-result.md)
- [8 题 × 3 次重复实验](experiments/2026-07-27-v2-repeated-results.md)
- [Adaptive V2 实验](experiments/2026-07-28-adaptive-v2-result.md)

## 正式命令

```powershell
.\scripts\run-v2.cmd direct
.\scripts\run-v2.cmd reflection
.\scripts\run-v2.cmd adaptive
.\scripts\test-v2.cmd
```
