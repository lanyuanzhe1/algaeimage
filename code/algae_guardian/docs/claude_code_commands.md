# Claude Code 命令速查表

## 斜杠命令 (Slash Commands)

| 命令 | 功能 | 用法示例 |
|------|------|----------|
| `/help` | 显示帮助信息 | `/help` |
| `/clear` | 清空当前对话上下文 | `/clear` |
| `/compact` | 压缩对话上下文，释放 token | `/compact` |
| `/config` | 打开/查看配置面板 | `/config` |
| `/model` | 切换模型 | `/model` (交互式选择) |
| `/fast` | 切换快速模式 (Opus 4.6 only) | `/fast` |
| `/init` | 初始化项目 CLAUDE.md | `/init` |
| `/review` | 审查当前分支的 PR | `/review` |
| `/security-review` | 安全审查当前分支变更 | `/security-review` |
| `/simplify` | 审查代码质量、复用和效率 | `/simplify` |
| `/add-dir` | 添加工作目录 (多目录上下文) | `/add-dir /path/to/dir` |
| `/permissions` | 管理工具权限 | `/permissions` |
| `/context` | 显示当前上下文信息 | `/context` |
| `/cost` | 显示当前会话 token 消耗 | `/cost` |
| `/todos` | 显示/管理任务列表 | `/todos` |
| `/status` | 显示当前会话状态 | `/status` |
| `/output-style` | 切换输出风格 (verbose/concise/explain) | `/output-style concise` |
| `/ide` | IDE 集成相关设置 | `/ide` |
| `/terminal-setup` | 终端集成安装 | `/terminal-setup` |
| `/memory` | 打开持久记忆管理 | `/memory` |
| `/agents` | 查看可用代理列表 | `/agents` |
| `/mcp` | MCP 服务器管理 | `/mcp` |
| `/hooks` | Hooks 配置管理 | `/hooks` |
| `/stats` | 查看会话统计信息 | `/stats` |
| `/bashes` | 查看后台运行任务 | `/bashes` |
| `/tasks` | 查看任务列表 | `/tasks` |
| `/doctor` | 诊断环境问题 | `/doctor` |
| `/update` | 更新 Claude Code | `/update` |
| `/upgrade` | 升级到最新版本 | `/upgrade` |
| `/version` | 显示当前版本 | `/version` |
| `/logout` | 退出登录 | `/logout` |
| `/login` | 登录账号 | `/login` |
| `/plan` | 进入计划模式 | `/plan` |
| `/worktree` | 管理 Git worktree | `/worktree` |
| `/loop` | 定时循环执行命令 | `/loop 5m /run-tests` |
| `/resume` | 恢复之前的会话 | `/resume` |
| `/export` | 导出当前对话 | `/export` |

## 键盘快捷键

| 快捷键 | 操作 | 说明 |
|--------|------|------|
| `Ctrl+Enter` | 提交消息 | 发送当前输入 |
| `Shift+Enter` | 插入换行 | 输入多行文本 |
| `Ctrl+C` | 中断 | 中断当前操作/生成 |
| `Ctrl+O` | 切换会话 | 查看/切换历史对话 |
| `Ctrl+L` | 清屏 | 清空终端显示 |
| `Ctrl+D` | 退出 | 退出 Claude Code |
| `Ctrl+R` | 搜索历史 | 反向搜索命令历史 |
| `Ctrl+Z` | 后台挂起 | 挂起 Claude Code |
| `Esc` | 取消输入 | 清空当前输入行 |
| `Tab` | 补全 | 路径/命令自动补全 |
| `↑/↓` | 历史命令 | 浏览输入历史 |
| `Ctrl+U` | 清空行 | 删除当前行 |
| `Ctrl+W` | 删除词 | 删除前一个词 |
| `Ctrl+A/E` | 行首/尾 | 光标移到行首/行尾 |
| `Ctrl+B/F` | 前/后一字 | 光标移动一个字 |

## Bash 模式标记

| 标记 | 含义 | 示例 |
|------|------|------|
| `!` | 在本会话执行命令 | `! gcloud auth login` |
| `&?` | 后台执行并通知 | `&? npm run build` |
| `%` | AI 辅助命令 (图灵企鹅) | `% ffmpeg ...` |

## 对话内命令

| 命令 | 功能 | 示例 |
|------|------|------|
| `<file>` | 直接引用文件路径 | `看看 src/main.py 的逻辑` |
| `@filename` | @文件引用 (IDE 集成) | `@src/utils.ts` |
| `#symbol` | 跳转到符号定义 | `点击 login 函数解释一下` |
| `L10-L20` | 引用行号范围 | `重构 src/main.py L10-L20` |

## 输出控制

| 命令 | 功能 |
|------|------|
| `--verbose` | 显示详细推理过程 |
| `--concise` | 精简输出模式 |
| `/output-style explain` | 解释模式 (教学风格) |
| `/output-style default` | 默认风格 |
| `@echo off` | 批量操作时不回显工具调用 |

## 配置文件

| 层级 | 路径 | 说明 |
|------|------|------|
| 用户级 | `~/.claude/settings.json` | 全局设置 (适用于所有项目) |
| 项目级 | `./.claude/settings.json` | 项目设置 (仅当前项目) |
| 本地级 | `./.claude/settings.local.json` | 本地设置 (不提交 git) |
| CLAUDE.md | `./CLAUDE.md` | 项目指令与上下文 |
| CLAUDE.local.md | `./CLAUDE.local.md` | 本地覆盖指令 (不提交 git) |
| 记忆 | `~/.claude/projects/<project>/memory/` | 跨会话持久记忆 |
| 键盘绑定 | `~/.claude/keybindings.json` | 自定义快捷键 |

## settings.json 常用配置项

| 配置项 | 类型 | 说明 |
|--------|------|------|
| `permissions.allow` | `string[]` | 允许的工具/命令列表 |
| `permissions.deny` | `string[]` | 禁止的工具/命令列表 |
| `env` | `object` | 环境变量注入 |
| `alwaysThinkingEnabled` | `bool` | 始终启用思考模式 |
| `model` | `string` | 默认模型选择 |
| `cleanupPeriodDays` | `int` | 自动清理旧会话 (天) |
| `hooks` | `object` | 自定义钩子 (事件触发) |

## 子代理类型

| 代理 | 用途 |
|------|------|
| `Explore` | 快速探索代码库、搜索文件/符号 |
| `Plan` | 设计实现方案、架构决策 |
| `general-purpose` | 通用复杂任务、多步执行 |
| `claude-code-guide` | Claude Code / API 使用咨询 |
| `code-reviewer` | 独立代码审查 |
| `workflow-builder` | 建立项目工作流 |
| `statusline-setup` | 配置状态栏显示 |

## 常用工作流

```bash
# 切换模型到 Opus 4.7
/model              # 然后选择 opus

# 快速模式 (Opus 4.6 加速输出)
/fast

# 定时检查构建状态 (每5分钟)
/loop 5m 检查构建状态

# 批量用 agent 探索代码
/agents explore  ←  或直接: Agent subagent_type=Explore

# 审查 PR
/review

# 初始化新项目
/init

# 查看 token 消耗
/cost

# 进入计划模式 (复杂任务前)
/plan

# 压缩上下文 (对话过长时)
/compact
```
