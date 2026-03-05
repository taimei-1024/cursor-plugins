# AI Technical Design (aitd)

AI 辅助技术设计全生命周期插件：需求分析 → 原型评审 → PRD 排雷 → 图表生成 → 设计评审。

---

## 快速开始

### 方式一：使用命令（推荐）

直接输入 `/` 即可看到所有可用命令：

```
/aitd-analyze-jira      分析 Jira 需求
/aitd-analyze-prototype 分析 AxShare 原型
/aitd-review-prd        PRD 排雷
/aitd-design-outline    生成设计大纲
/aitd-api-contract      生成 API 契约表
/aitd-table-spec        提取表结构
/aitd-flowchart         生成流程图
/aitd-mock-review       模拟评审
/aitd-security-check    安全自查
/aitd-review            正式评审
```

### 方式二：自然语言

直接描述你的需求，无需记忆：

```
分析 Jira 需求 PVS-123
生成技术设计文档大纲
帮我画个流程图
提取这个表的字段结构
评审技术设计
```

---

## 命令详解

### 需求分析

| 命令 | 用途 | 示例 |
|------|------|------|
| `/aitd-analyze-jira` | 分析 Jira 需求详情 | `/aitd-analyze-jira PVS-123` |
| `/aitd-analyze-prototype` | 分析 AxShare 原型 | `/aitd-analyze-prototype https://xxx.axshare.com` |
| `/aitd-review-prd` | PRD 排雷找问题 | `/aitd-review-prd <PRD 内容>` |

### 技术设计

| 命令 | 用途 | 示例 |
|------|------|------|
| `/aitd-design-outline` | 生成文档大纲 | `/aitd-design-outline 总体设计` |
| `/aitd-api-contract` | 生成 API 契约表 | `/aitd-api-contract <Controller 代码>` |
| `/aitd-table-spec` | 提取表结构 | `/aitd-table-spec <DDL 语句>` |
| `/aitd-flowchart` | 生成流程图/架构图 | `/aitd-flowchart <流程描述>` |

### 评审

| 命令 | 用途 | 示例 |
|------|------|------|
| `/aitd-mock-review` | 模拟评审准备 | `/aitd-mock-review <设计文档>` |
| `/aitd-security-check` | 安全漏洞自查 | `/aitd-security-check <设计文档>` |
| `/aitd-review` | 正式技术设计评审 | `/aitd-review PVS-XXX <文档URL>` |

---

## 完整工作流示例

### 新功能开发

```
/aitd-analyze-jira PVS-123
/aitd-analyze-prototype https://xxx.axshare.com
/aitd-review-prd <PRD 内容>
/aitd-design-outline 总体设计
/aitd-flowchart 生成创建报告的流程图
/aitd-table-spec <DDL 语句>
/aitd-api-contract <Controller 代码>
/aitd-mock-review
/aitd-security-check
/aitd-review PVS-123 https://xxx.confluence.com
```

---

## 功能对照表

| 自然语言 | 命令 | 说明 |
|----------|------|------|
| 分析 Jira、查看需求 | `/aitd-analyze-jira` | 获取需求详情 |
| 分析原型、查看原型 | `/aitd-analyze-prototype` | 原型截图分析 |
| 排雷、预审、对齐 | `/aitd-review-prd` | PRD 前置审计 |
| 生成大纲、文档模板 | `/aitd-design-outline` | 文档骨架生成 |
| API 清单、接口文档 | `/aitd-api-contract` | 接口契约表 |
| 表结构、数据模型 | `/aitd-table-spec` | 表结构提取 |
| 流程图、架构图 | `/aitd-flowchart` | 技术设计图 |
| 模拟评审、评审准备 | `/aitd-mock-review` | 预演评审 |
| 安全自查、安全检查 | `/aitd-security-check` | 安全扫描 |
| 评审技术设计 | `/aitd-review` | 正式评审 |

---

## 知识库闭环

每次评审后，AI 会自动更新项目的 `MEMORY.md` 文件，形成知识积累：

```
设计 → 评审 → 问题 → MEMORY.md → 下一次设计（参考历史）
```

### MEMORY.md 内容

| 类别 | 说明 |
|------|------|
| **常见问题** | 历次评审发现的重复问题，避免再次犯错 |
| **设计规范** | 从优秀设计中提炼的规范和模式 |
| **技术债务** | 需要后续处理的技术问题 |
| **项目上下文** | 技术栈、中间件、关键表等信息 |

### 闭环示例

```
第一次评审：发现 ARCH-002 模块划分不清晰
    ↓
写入 MEMORY.md → 常见问题 / 架构设计
    ↓
第二次设计：AI 提醒"注意模块职责单一性"
    ↓
第二次评审：模块划分清晰，通过 ✅
```

---

## MCP 依赖

本插件依赖以下环境已有的 MCP 服务（无需在插件中重复声明）：

- **tm-jira** — Jira / Confluence 数据获取
- **chrome-devtools** — 浏览器页面导航与截图
- **zai-mcp-server** — 图片分析与 UI 识别
