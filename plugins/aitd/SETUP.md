# AITD Plugin Setup Guide

本指南说明如何配置 aitd 插件所需的 MCP 服务器。

---

## Required MCP Servers

### 1. tm-jira (Jira / Confluence)

**用途**: 获取 Jira 需求详情、Confluence 技术设计文档

**所需工具**:
- `jira_get_issue` - 获取工单详情
- `confluence_get_page` - 获取 Confluence 页面内容

**配置方式**:
在 Claude MCP 配置中添加 tm-jira 服务器。该服务器需要在环境中单独安装和配置。

**配置示例**:
```json
{
  "mcpServers": {
    "tm-jira": {
      "command": "node",
      "args": ["/path/to/tm-jira-server/index.js"],
      "env": {
        "JIRA_BASE_URL": "https://your-jira.com",
        "JIRA_TOKEN": "your-token",
        "CONFLUENCE_BASE_URL": "https://your-confluence.com"
      }
    }
  }
}
```

---

### 2. chrome-devtools (浏览器自动化)

**用途**: 访问 AxShare 原型页面，获取截图

**所需工具**:
- `navigate_page` - 导航到目标 URL
- `take_screenshot` - 页面截图
- `evaluate_script` - 执行 JavaScript

**配置方式**:
chrome-devtools 是 Claude Code 内置的 MCP 工具，无需额外安装。只需在 Claude Code 设置中启用即可。

**检查可用性**:
在 Claude Code 中输入 `/mcp` 或检查 MCP 连接状态，确认 chrome-devtools 已连接。

---

### 3. zai-mcp-server (图片分析)

**用途**: 分析需求截图、原型截图，提取 UI 内容和交互信息

**所需工具**:
- `analyze_image` - 图片内容分析
- `ui_to_artifact` - UI 转描述/代码
- `extract_text_from_screenshot` - 提取截图文字

**配置方式**:
外部 MCP 服务器，需要单独安装和配置。

**配置示例**:
```json
{
  "mcpServers": {
    "zai-mcp-server": {
      "command": "python",
      "args": ["-m", "zai_mcp_server"],
      "env": {
        "OPENAI_API_KEY": "your-api-key"
      }
    }
  }
}
```

---

## MCP Tool Mapping

| Skill | Required MCP Tools |
|-------|-------------------|
| `analyze-jira` | `mcp__tm-jira__jira_get_issue`<br>`mcp__zai-mcp-server__analyze_image` |
| `axshare` | `mcp__chrome-devtools__navigate_page`<br>`mcp__chrome-devtools__take_screenshot`<br>`mcp__chrome-devtools__evaluate_script`<br>`mcp__zai-mcp-server__ui_to_artifact` |
| `tech-design-review` | `mcp__tm-jira__jira_get_issue`<br>`mcp__tm-jira__confluence_get_page` |
| `align-master` | 无需 MCP（基于代码上下文分析） |
| `flowchart` | 无需 MCP（生成 XML 文件） |
| `table-spec` | 可选：数据库 MCP（如需要从数据库直接获取表结构） |

---

## Troubleshooting

### Issue: "MCP tool not found"

**症状**: 执行命令时报错找不到 MCP 工具

**解决方案**:
1. 检查 MCP 服务器是否正确配置
2. 在 Claude Code 中运行 `/mcp` 查看已连接的 MCP 服务器
3. 重启 Claude Code 使 MCP 配置生效

---

### Issue: "AxShare iframe not loading"

**症状**: AxShare 原型分析时截图内容为空或不完整

**解决方案**:
1. 检查网络连接是否正常
2. 增加 `navigate_page` 的等待时间
3. 确保 chrome-devtools MCP 正常运行
4. 尝试直接访问 iframe URL（axshare skill 会自动处理）

---

### Issue: "Jira authentication failed"

**症状**: 无法获取 Jira 工单信息

**解决方案**:
1. 检查 tm-jira MCP 配置中的 JIRA_TOKEN 是否有效
2. 确认 JIRA_BASE_URL 正确
3. 验证 Token 权限是否包含读取工单的权限

---

### Issue: "图片分析失败"

**症状**: analyze-jira 或 axshare 无法分析图片

**解决方案**:
1. 检查 zai-mcp-server 是否正常运行
2. 确认 OpenAI API Key 有效且有额度
3. 查看图片格式是否支持（png, jpg, jpeg, gif）

---

## 验证安装

运行以下命令验证 MCP 配置是否正确：

```bash
# 在 Claude Code 中
/aitd-analyze-jira TM-123      # 测试 tm-jira 连接
/aitd-analyze-prototype https://xxx.axshare.com  # 测试 chrome-devtools + zai-mcp-server
```

---

## 最低配置要求

- **必须**: tm-jira (用于 Jira 需求获取)
- **必须**: zai-mcp-server (用于图片分析)
- **可选**: chrome-devtools (仅当需要 AxShare 原型分析时)
