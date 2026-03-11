---
name: analyze-jira
description: 从 Jira 获取需求详情、分析附件图片、输出结构化需求分析文档。当用户提及 Jira 工单、需求详情、查看需求、任何 Jira 工单号（如 TM-XXX、PVS-XXX、PROJ-123 等格式）、分析 Jira、"帮我看下这个需求" 时触发。
---

## Purpose

分析 Jira 工单，提取需求描述、附件中的图片内容，输出结构化的需求分析文档。

## Tools

- **mcp__tm_jira**: Jira MCP server (tm-jira)
  - `jira_get_issue`: 获取工单详情
  - `jira_get_attachments`: 获取附件列表

- **mcp__zai-mcp-server__analyze_image**: 图片分析
  - 分析需求中的截图、设计图等

## Parameters

- `jira_key` (required): Jira 工单号，如 TM-123 或完整 URL

## Instructions

1. **解析输入**：从用户输入中提取 Jira Key
   - 支持格式：`TM-123` 或 `http://jira.taimei.com/browse/TM-123`
   - 转换为大写

2. **获取工单详情**：
   - 调用 `jira_get_issue` 获取工单信息
   - 提取字段：`summary`、`description`、`attachments`、`comments`

3. **分析图片附件**：
   - 遍历 attachments 中的图片文件（png, jpg, jpeg, gif）, 下载到临时目录
   - 对下载后的每张图片调用 `mcp__zai-mcp-server__analyze_image`
   - 分析 prompt：`"详细描述这张图片的内容，包括UI布局、文字说明、交互元素等，用于理解产品需求"`

4. **输出结构化需求分析**：

   ```markdown
   ## 需求概述
   {summary}

   ## 详细描述
   {description}

   ## 图片分析
   {图片内容分析...}

   ## 验收标准
   {从 description 或 comments 中提取}

   ## 其他信息
   - 报告人：{reporter}
   - 优先级：{priority}
   - 状态：{status}
   ```

## Usage

```
use analyze-jira TM-123
```

或

```
use analyze-jira http://jira.taimei.com/browse/TM-123
```

## Example Output

```markdown
## 需求概述
用户登录页面增加验证码功能

## 详细描述
当前登录页面存在暴力破解风险，需要增加图形验证码...

## 图片分析
![附件1](url)
该图展示了登录页面的新设计，包含用户名输入框、密码输入框和验证码输入框...

## 验收标准
- 验证码为4位字母数字组合
- 验证码有效期60秒
- 输入错误3次后锁定账户5分钟
```
