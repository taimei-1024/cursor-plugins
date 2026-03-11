# AxShare DOM 结构参考

## 页面结构

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

## 选择器

- 目录容器: `#sitemapTreeContainer ul li a.sitemapPageLink`
- 页面名: `a.sitemapPageLink span.sitemapPageName`
- 页面URL: `a.sitemapPageLink[nodeurl]`
- 内容 iframe: `#mainFrame`

## 提取所有页面信息的脚本

```javascript
() => {
  const links = document.querySelectorAll('a.sitemapPageLink');
  return Array.from(links).map(link => ({
    title: link.querySelector('.sitemapPageName')?.textContent || link.textContent,
    nodeurl: link.getAttribute('nodeurl')
  }));
}
```
