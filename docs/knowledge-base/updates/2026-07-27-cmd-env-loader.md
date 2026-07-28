# 纯 CMD 环境加载器

Windows PowerShell 5 的执行策略和 UTF-8 脚本解析会影响 `.ps1` 包装器。最终方案改为
纯 `.cmd` 启动器，直接读取项目根目录 `.env`，无需改变系统执行策略。

