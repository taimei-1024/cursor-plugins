---
name: axshare
description: 访问 AxShare 原型页面，提供截图和文本识别功能
---

## Purpose

访问 AxShare 原型页面 (https://d9faxa.axshare.com/)，提供：
1. **截图功能** - 获取页面可视区域的截图
2. **文本识别** - 提取页面中的文字内容
3. **多页面支持** - 遍历原型中的所有页面

## Tools

- **mcp__chrome-devtools__navigate_page**: 导航到指定 URL
- **mcp__chrome-devtools__take_screenshot**: 页面截图（支持全页）
- **mcp__chrome-devtools__evaluate_script**: 执行 JavaScript
- **mcp__zai-mcp-server__ui_to_artifact**: UI 转描述/代码（主要分析工具）
- **mcp__zai-mcp-server__extract_text_from_screenshot**: 提取截图中的文字

## Parameters

- `url` (required): AxShare 页面 URL，如 `https://d9faxa.axshare.com/`
- `action` (optional): 操作类型
  - `screenshot`: 仅截图
  - `text`: 仅提取文本
  - `all`: 同时获取截图和文本（默认）
  - `list`: 列出所有页面
  - `capture-all`: 抓取所有页面

## Instructions

### 1. 解析输入

```javascript
// 从用户输入中提取 URL 和操作类型
// 例如: "use axshare https://d9faxa.axshare.com/ screenshot"
```

### 2. 单页面操作

#### 截图 + 分析 (默认/all)

**关键**: AxShare 页面使用 iframe 展示内容，必须直接访问 iframe URL 才能完整截图。

1. 使用 `navigate_page` 导航到目标 URL（`{type: "url", url: "目标URL"}`）
2. 等待页面加载完成（等待 `#mainFrame` 出现）
3. 使用 `evaluate_script` 获取 iframe 的 src 地址:

```javascript
() => {
  const iframe = document.querySelector('#mainFrame');
  return iframe ? iframe.src : null;
}
```

4. 使用 `navigate_page` 直接导航到 iframe URL（`{type: "url", url: "iframeURL"}`）
5. 等待内容加载完成
6. **滚动触发懒加载，确保滚动内容被截取**:

```javascript
() => {
  // 滚动到页面底部，触发懒加载内容
  window.scrollTo(0, document.body.scrollHeight);
  // 等待 500ms 让内容加载
  return new Promise(resolve => setTimeout(() => {
    // 滚回顶部
    window.scrollTo(0, 0);
    resolve({
      scrollHeight: document.body.scrollHeight,
      clientHeight: document.documentElement.clientHeight
    });
  }, 500));
}
```

7. 使用 `take_screenshot` 获取**全页截图**（`{fullPage: true}` 或 `filePath: "/tmp/xxx.png"`）:

```
filePath: /tmp/axshare_{timestamp}.png
fullPage: true
```

8. 使用 `evaluate_script` 提取 DOM 文字（辅助）:

```javascript
() => {
  return document.body.innerText;
}
```

9. 使用 `mcp__zai-mcp-server__ui_to_artifact` 分析截图（主要）:

```
image_source: /tmp/axshare_{timestamp}.png
output_type: description
prompt: "详细分析这个 AxShare 原型页面的布局、组件、交互元素和功能。输出描述：1) 整体布局结构 2) 主要UI组件 3) 文字内容和标签 4) 交互元素（按钮、输入框、链接等） 5) 交互说明(红色字和线)"
```

10. **请作为资深产品经理，基于该原型截图和 DOM 文字，撰写一份结构化的【产品原型说明书】。要求：1) 页面概述：简述页面用途及场景；2) 区域划分：按视觉逻辑划分模块；3) 字段详情：以表格形式列出（字段名称、类型、是否必填、说明/逻辑）；4) 交互逻辑：描述点击、联动、校验、下拉选项等。不要发挥，不要缺漏，严谨对齐原型内容。**（参考以图片为主，DOM 文字为辅）

#### 仅截图 (screenshot)

步骤同上，只执行 1-7 步，返回截图文件路径。

#### 提取文本 (text)

1. 使用 `navigate_page` 导航到目标 URL（`{type: "url", url: "目标URL"}`）
2. 等待页面加载完成
3. 使用 `evaluate_script` 获取 iframe src 并导航
4. 使用 `evaluate_script` 提取页面文本
5. 返回格式化的文本

### 3. 多页面操作

#### 列出所有页面 (list)

AxShare DOM 结构:

```
┌─────────────────┬──────────────────┐
│  左侧目录        │   右侧 iframe     │
│  #sitemapTree   │   #mainFrame     │
├─────────────────┼──────────────────┤
│ <a class="      │                  │
│  sitemapPageLink│  动态加载的页面   │
│  nodeurl="xxx"  │                  │
│  >页面名</a>    │                  │
└─────────────────┴──────────────────┘
```

选择器:

- 目录容器: `#sitemapTreeContainer ul li a.sitemapPageLink`
- 页面名: `a.sitemapPageLink span.sitemapPageName`
- 页面URL: `a.sitemapPageLink[nodeurl]`
- 内容 iframe: `#mainFrame`

操作步骤:

1. 使用 `navigate_page` 导航到主 URL（`{type: "url", url: "主URL"}`）
2. 等待 `#sitemapTreeContainer` 加载
3. 使用 `evaluate_script` 提取所有页面信息:

```javascript
() => {
  const links = document.querySelectorAll('a.sitemapPageLink');
  return Array.from(links).map(link => ({
    title: link.querySelector('.sitemapPageName')?.textContent || link.textContent,
    nodeurl: link.getAttribute('nodeurl')
  }));
}
```

4. 返回页面列表数组

#### 抓取所有页面 (capture-all)

1. 先执行 `list` 操作获取所有页面
2. 对每个页面:
   a. 构造完整 iframe URL: `{baseUrl}/{nodeurl}`
   b. 使用 `navigate_page` 导航到 iframe URL（`{type: "url", url: "iframeURL"}`）
   c. 等待内容加载完成
   d. **滚动触发懒加载**:

   ```javascript
   () => {
     window.scrollTo(0, document.body.scrollHeight);
     return new Promise(resolve => setTimeout(() => {
       window.scrollTo(0, 0);
       resolve({ scrollHeight: document.body.scrollHeight });
     }, 500));
   }
   ```

   e. 使用 `take_screenshot` 获取**全页截图**，保存到 `/tmp/axshare_{index}_{pagename}.png`

   ```
   filePath: /tmp/axshare_{index}_{pagename}.png
   fullPage: true
   ```

   f. 使用 `evaluate_script` 提取 DOM 文字（辅助）
   g. 使用 `mcp__zai-mcp-server__ui_to_artifact` 分析截图（主要）
3. **结合所有页面的图片分析和 DOM 文字，输出完整原型描述**（图片为主，DOM 为辅）

### 4. 输出格式

#### 单页面结果

```markdown
## AxShare 原型分析

**URL**: {url}
**截图**: `/tmp/axshare_{timestamp}.png`

---

## 产品原型说明书

### 一、页面概述

{页面用途及业务场景}

---

### 二、区域划分

| 序号 | 区域名称 | 位置 | 功能描述 |
|-----|---------|------|---------|
| 1 | {区域名} | {位置} | {描述} |
| 2 | {区域名} | {位置} | {描述} |
...

---

### 三、字段详情

#### 3.1 {区域名称}

| 字段名称 | 类型 | 是否必填 | 说明/逻辑 |
|---------|------|---------|----------|
| {字段名} | {类型} | {是/否/条件必填} | {说明} |

或表格形式：

| 部位 | 测量值 |
|-----|-------|
| {部位名} | {输入类型} |

---

### 四、交互逻辑

#### 4.1 显隐联动
- {联动规则描述}

#### 4.2 校验规则

| 字段 | 校验规则 |
|-----|---------|
| {字段名} | {规则} |

#### 4.3 输入限制
- {限制说明}

#### 4.4 下载/其他功能
- {功能说明}

---

### 五、区域结构汇总

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              {区域名称}                                      │
│      {内容布局示意}                                                          │
├──────────────────────────────────────────────────────────────────────────────┤
│                              {区域名称}                                      │
│      {内容布局示意}                                                          │
└──────────────────────────────────────────────────────────────────────────────┘
```

注意：
- 区域结构汇总使用 ASCII 字符绘制页面布局
- 表格用 ┌─┬┐├─┼┤└─┴┘ 等字符绘制
- 对齐要工整，清晰展示页面布局关系
```

#### 多页面列表

```markdown
## AxShare 页面目录

**URL**: {url}

共找到 {count} 个页面:

1. **{页面名}**
   - URL: {nodeurl}

2. **{页面名}**
   - URL: {nodeurl}
...
```

#### 所有页面抓取结果

```markdown
## AxShare 完整原型分析

**URL**: {url}
**页面数量**: {count}

---

### 页面 1: {页面名}
**截图**: `/tmp/axshare_1_{pagename}.png`

#### 产品原型说明书
{按上述单页面格式生成的结构化说明书}


---

### 页面 2: {页面名}
...
```

## Usage

```
use axshare https://d9faxa.axshare.com/
```

默认操作: 同时获取截图和文本

```
use axshare https://d9faxa.axshare.com/ screenshot
```

仅截图

```
use axshare https://d9faxa.axshare.com/ text
```

仅提取文本

```
use axshare https://d9faxa.axshare.com/ list
```

列出所有页面

```
use axshare https://d9faxa.axshare.com/ capture-all
```

抓取所有页面

## Example

```
use axshare https://d9faxa.axshare.com/ list
```

输出:

```markdown
## AxShare 页面目录

**URL**: https://d9faxa.axshare.com/

共找到 5 个页面:

1. **首页**
   - URL: 首页.html

2. **超声访视评估**
   - URL: 超声访视评估.html

3. **数据导出**
   - URL: 数据导出.html
...
```

## Prerequisites

使用此 skill 前需要确保已配置 chrome-devtools MCP 服务器。

chrome-devtools 是 Claude Code 内置的 MCP 工具，无需额外安装，只需确保在配置中启用即可。

## Troubleshooting

- **页面加载超时**: AxShare 页面可能需要较长时间加载，增加等待时间
- **iframe 无法访问**: 某些页面可能有跨域限制，尝试直接访问 iframe URL
- **截图内容不完整**: 使用滚动触发懒加载，并设置 height 参数为 scrollHeight 确保完整截图
- **截图为空**: 等待页面元素加载完成后再截图
