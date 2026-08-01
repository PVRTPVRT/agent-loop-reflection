# ADR-001：AI 生成代码必须默认在 Docker 沙箱中执行

- 状态：已实施
- 决策日期：2026-07-27
- 验证更新：2026-08-01

## 背景

Coder 输出与候选 Repository Patch 都是不可信输入。早期原型曾允许在 Docker 不可用
时回退到宿主机 `exec()`；这会让生成代码访问用户文件、网络、凭据或子进程，因此不能
进入正式执行路径。

## 决策

所有候选代码只允许在 Managed Docker 中执行。Docker、固定镜像或容器生命周期不可用
时返回安全错误，不提供 `ALLOW_UNSAFE_LOCAL_EXEC` 或任何隐式宿主机回退。

容器采用：

- 固定 OCI image digest；
- 禁止网络；
- 只读根文件系统和只读候选挂载；
- 清空 Linux capabilities 并启用 `no-new-privileges`；
- 非 root 用户；
- CPU、内存和 PID 限额；
- 受限 `/tmp` tmpfs；
- 命名容器、宿主机超时和 `finally` 强制删除。

## 后果

- Docker 故障会降低可用性，但不会静默降低安全等级。
- 函数与仓库验证共享一个容器生命周期，减少安全控制分叉。
- Docker 不是恶意代码的绝对安全边界；处理高价值私有仓库时仍应使用独立工作节点或
  microVM 等更强隔离。
