# Cursor Trial Plugins

太美团队的 Cursor 插件市场，包含一组内部插件。

## 包含的插件

- **aitd**: AI 辅助技术设计：需求分析、原型评审、PRD 排雷、图表生成、设计评审
- **cursor-blame**: Cursor AI 代码溯源：追踪 git 提交到 Cursor 对话，查看 AI 贡献统计
- **confluence-editor**: 读取和编辑 Confluence 页面内容，支持表格列操作、文本替换、章节修改等

## 仓库结构

- `.cursor-plugin/marketplace.json`: 市场清单与插件注册表
- `plugins/<plugin-name>/.cursor-plugin/plugin.json`: 各插件元数据
- `plugins/<plugin-name>/rules`: 规则文件（`.mdc`）
- `plugins/<plugin-name>/skills`: 技能目录，包含 `SKILL.md`
- `plugins/<plugin-name>/agents`: 子代理定义
- `plugins/<plugin-name>/mcp.json`: 各插件的 MCP 服务器配置

## 校验变更

运行：

```bash
node scripts/validate-template.mjs
```

该脚本会检查市场路径、插件清单，以及规则/技能/代理/命令文件中的必填 frontmatter。

## 提交检查清单

- 每个插件都有有效的 `.cursor-plugin/plugin.json`
- 插件名称唯一，使用小写 kebab-case 格式
- `.cursor-plugin/marketplace.json` 中的条目对应实际的插件目录
- 插件内容文件中包含必填的 frontmatter 元数据
- Logo 路径在各插件清单中可正确解析
- `node scripts/validate-template.mjs` 通过
