---
name: cursor-blame
description: 通过 git commit 反查产生该 commit 的 Cursor AI 对话，查看文件级行归因、AI 贡献占比、模型追踪、对话上下文。当用户提及"cursor blame"、"AI 代码归因"、"这个 commit 是 AI 写的吗"、"查看 AI 对话"、"AI 贡献统计"、"哪些代码是 AI 生成的"、"追溯 commit 对话"、"AI 代码占比"、"这个文件哪些是 AI 写的"、commit hash + "对话"/"conversation" 时触发。也适用于用户想了解某段代码的 AI 生成上下文、查看 Cursor 对话历史、或分析项目的 AI 辅助编码情况。
---

## Purpose

本地版 Cursor Blame，通过读取 Cursor 本地数据库，实现四大功能：

1. **AI Attribution** -- 逐行标注哪些代码来自 AI（composer/tab），哪些是人工编写
2. **Model Tracking** -- 追踪每段代码由哪个模型生成（claude-4.6-opus、gpt-5.3-codex 等）
3. **Conversation Context** -- 查看产生代码的 Cursor 对话摘要，追溯编码决策过程
4. **Contribution Breakdown** -- 可视化显示每个 commit/文件中 AI 与人工的代码贡献占比

## Data Sources

Cursor 在本地存储的 AI 代码追踪数据：

- `~/.cursor/ai-tracking/ai-code-tracking.db` -- commit 评分 + 行级归因 + conversationId
- `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb` -- 对话元数据 + 消息内容

## Script

脚本路径（相对于本 SKILL.md）：`scripts/cursor_blame.py`

纯 Python 标准库实现，无需安装依赖。

## Commands

### 1. commit -- AI attribution + contribution breakdown (推荐)

```bash
python3 {SCRIPT_PATH} commit <commit-hash> [-v]
```

查看一个 commit 的完整 AI 归因报告：
- 贡献占比条形图（Composer / Tab / Human）
- 每个变更文件的 AI 来源标注和模型信息
- 关联的 Cursor 对话摘要（含首条用户消息）
- `-v` 展开对话的完整消息

**自动处理 merge commit**: 检测到 merge commit 时自动展开分析内部的实际 commit。

### 2. file -- 文件级逐行 AI 归因

```bash
python3 {SCRIPT_PATH} file <filepath> [-L <range>] [--no-lines]
```

结合 `git blame` 与 AI tracking 数据，为文件每一行标注：
- 来源：composer（Agent 生成）/ tab（补全）/ human
- AI 占比（来自 scored_commits）
- 对应的 commit 和作者

输出包含：
- **Contribution Breakdown**: 文件整体的 AI/Human 代码占比条形图
- **Models Used**: 此文件用过的 AI 模型列表
- **Related Conversations**: 关联的对话摘要
- **Line Attribution**: 逐行归因表（可用 `--no-lines` 隐藏）

`-L 1,20` 限制行范围，语法同 `git blame -L`。

### 3. blame -- commit -> 完整对话内容

```bash
python3 {SCRIPT_PATH} blame <commit-hash> [-s] [-n 20]
```

追溯 commit 关联的 Cursor 对话并显示完整消息。当需要看对话详情时使用。

### 4. log -- 批量查看 AI commit 列表

```bash
python3 {SCRIPT_PATH} log [--since YYYY-MM-DD] [--until YYYY-MM-DD] [-n 50]
```

### 5. chat -- 直接查看对话

```bash
python3 {SCRIPT_PATH} chat <conversation-id> [-s]
```

### 6. stats -- 汇总统计

```bash
python3 {SCRIPT_PATH} stats
```

## Instructions

1. **脚本路径**: 用本 SKILL.md 同级 `scripts/cursor_blame.py` 的绝对路径。

2. **工作目录**: commit/file/blame 命令必须在目标 git 仓库目录下执行。先确认用户指定的 commit/file 属于哪个仓库。

3. **选择命令**:
   - 用户给 commit hash -> 用 `commit`（概览）或 `blame`（看对话）
   - 用户问某个文件 -> 用 `file`
   - 用户想看整体统计 -> 用 `stats`
   - 用户想看某段时间的 commit -> 用 `log`

4. **解读输出**:
   - `composer` = Cursor Composer/Agent 生成
   - `tab` = Cursor Tab 自动补全
   - `human` = 人工编写
   - `v2AiPercentage` 是 Cursor 官方的 AI 代码百分比
   - 一个 commit 可能关联多个对话（多轮交互产出）

5. **Merge commit**: `commit` 命令自动检测并展开 merge commit 内部的实际 commit。

## Limitations

- 数据范围取决于 Cursor 本地 DB 保留时长
- Tab 补全通常没有 conversationId，无法追溯对话
- 文件级归因基于 commit 粒度（同一 commit 的所有行标注相同来源）
- 仓库重命名/移动过时，使用相对路径模糊匹配兼容
- 只读访问，不修改任何数据
