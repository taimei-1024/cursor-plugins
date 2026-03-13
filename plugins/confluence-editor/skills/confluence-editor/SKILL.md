---
name: confluence-editor
description: 读取和编辑 Confluence 页面内容。支持删除/添加表格列、修改单元格、更新章节、追加内容等操作。当用户提到"编辑 Confluence"、"修改 wiki 页面"、"更新 CF 文档"、"删除表格列"、"cf.taimei.com"、"pageId" 时触发。
---

## Purpose

读取 Confluence 页面的 storage HTML 内容，在本地执行编辑操作，然后通过 REST API 回写。始终使用 storage HTML 格式 + REST API 直接调用（不走 MCP 回写，不用 markdown 格式）。

## Tools

- **mcp__tm-jira__confluence_get_page**: 获取页面 markdown 预览（仅用于展示给用户）
- **Bash**: 运行 `scripts/cf_api.py` 和 `scripts/edit_table.py`

## Scripts

脚本位于 `${SKILL_DIR}/scripts/` 目录下：
- `cf_api.py` — Confluence REST API 封装（获取/更新页面/添加标签）
- `edit_table.py` — 表格编辑工具（删除/添加列）

## Instructions

### Step 1: 解析页面 URL

从用户提供的 URL 中提取 `pageId`：
- URL 格式：`http://cf.taimei.com/pages/viewpage.action?pageId=165376373`
- 提取 `pageId=` 后面的数字

### Step 2: 获取页面内容（两步并行）

同时执行：

1. **MCP 预览**（用于向用户展示）：
   ```
   confluence_get_page(page_id=<pageId>, convert_to_markdown=true)
   ```

2. **REST API 获取完整 storage HTML**（用于编辑）：
   ```bash
   python3 ${SKILL_DIR}/scripts/cf_api.py get <pageId>
   ```
   输出 JSON 包含 `title`、`version`、`content`，content 会保存到 `/tmp/cf_page_<pageId>.html`

### Step 3: 用户确认编辑意图

向用户展示 markdown 预览内容，确认要执行的操作。明确告知将要做什么修改。

### Step 4: 执行编辑

根据操作类型选择不同方式，所有操作都在 storage HTML 文件上进行：

#### 表格操作（删除/添加列）

```bash
# 删除列（table_index 和 col_index 从 0 开始）
python3 ${SKILL_DIR}/scripts/edit_table.py remove-column /tmp/cf_page_<pageId>.html /tmp/cf_page_<pageId>_updated.html <table_index> <col_index>

# 添加列
python3 ${SKILL_DIR}/scripts/edit_table.py add-column /tmp/cf_page_<pageId>.html /tmp/cf_page_<pageId>_updated.html <table_index> <col_index> "列标题"
```

#### 文本替换

直接用 Python 在 storage HTML 上做字符串操作：
```bash
python3 -c "
with open('/tmp/cf_page_<pageId>.html') as f:
    html = f.read()
html = html.replace('旧文本', '新文本')
with open('/tmp/cf_page_<pageId>_updated.html', 'w') as f:
    f.write(html)
"
```

#### 章节修改

定位 `<h2>`/`<h3>` 标签，替换对应区间的内容。保留所有 Confluence 宏。

### Step 5: 回写页面

```bash
python3 ${SKILL_DIR}/scripts/cf_api.py update <pageId> "<title>" /tmp/cf_page_<pageId>_updated.html <version> "修改说明"
```

- `<version>` 是 Step 2 获取的当前版本号（脚本会自动 +1）
- 返回新版本号确认成功

回写成功后，自动为页面添加 AI 归因标签：

```bash
python3 ${SKILL_DIR}/scripts/cf_api.py label <pageId> ai-assisted co-authored-by-<model>
```

其中 `<model>` 由 AI 根据自身模型名称填写（如 `claude-opus-4-6`），格式统一为小写加连字符。该 API 是幂等的，重复添加不会报错。

### Step 6: 告知用户

- 提供页面链接：`http://cf.taimei.com/pages/viewpage.action?pageId=<pageId>`
- 提醒可通过 Confluence 版本历史回退

## Critical Notes

以下是从实际编辑经验中总结的关键注意事项：

1. **colgroup 正则陷阱**：`<col[^/]*/>` 会误匹配 `<colgroup>`，必须用 `<col\s[^>]*/>`
2. **嵌套标签处理**：`<td>` 内可能包含嵌套的 `<td>`（如嵌套表格），需用 depth 计数来正确定位单元格边界
3. **HTTP→HTTPS**：Confluence 可能 301 重定向，PUT 请求必须直接用 HTTPS（`https://cf.taimei.com`）
4. **storage 格式是 XHTML**：必须保持 XML 合法性，自闭合标签用 `<br/>`、`<col .../>`
5. **大内容不能通过 MCP 工具传递**：始终用 REST API + 文件读写
6. **SSL 证书**：内部 Confluence 需要跳过 SSL 验证
7. **编辑前务必备份**：content 保存到 `/tmp/cf_page_<pageId>.html` 即为备份
