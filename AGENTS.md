# 项目开发规范

## 双平台支持

本仓库同时支持 Cursor 和 Claude Code 两个平台。所有变更必须保持双平台一致。

### 新增插件

1. 在 `plugins/<plugin-name>/` 下同时创建两个清单目录：
   - `.cursor-plugin/plugin.json`
   - `.claude-plugin/plugin.json`
2. 在两个市场文件中都注册该插件：
   - `.cursor-plugin/marketplace.json`
   - `.claude-plugin/marketplace.json`

### 新增 Skill

新增或修改 skill 时，确保同时更新两个平台的插件清单和市场注册，不可只更新一侧。

### 检查清单

- [ ] `plugins/<name>/.cursor-plugin/plugin.json` 存在
- [ ] `plugins/<name>/.claude-plugin/plugin.json` 存在
- [ ] `.cursor-plugin/marketplace.json` 已注册
- [ ] `.claude-plugin/marketplace.json` 已注册
- [ ] 两侧描述、版本等信息保持一致
