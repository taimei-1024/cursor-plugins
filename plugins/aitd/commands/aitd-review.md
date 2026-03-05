---
name: aitd-review
description: 执行技术设计评审，按 39 项检查清单评审并生成结构化报告
---

# 评审技术设计

请使用 tech-design-review 技能执行正式技术设计评审。

**使用方式**：
- `/aitd-review PVS-XXX <文档URL>`
- `/aitd-review`

**必须信息**：
- Jira Key（格式：PVS-XXX）
- Confluence 技术设计文档 URL
- 需求类型（新功能开发 / 功能迭代 / 技术优化）

**输出内容**：
- 39 项检查清单评审结果
- 评审报告（保存至 reviews/ 目录）
- 评审结果判定（通过/有条件通过/需要修改）
- 钉钉通知发送

---

如果缺少必须信息，请询问用户提供。
