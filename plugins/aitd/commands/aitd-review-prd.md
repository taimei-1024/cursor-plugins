---
name: aitd-review-prd
description: 产研测需求对齐排雷手，对 PRD 做前置审计，挖掘逻辑漏洞与实现冲突
---

# PRD 排雷

请使用 align-master 技能对 PRD 文档进行排雷分析。

**使用方式**：
- `/aitd-review-prd <PRD 内容>`
- `/aitd-review-prd`

**输出内容**：
- 业务本质提炼
- 未定义异常流
- 逻辑矛盾点
- 与现有代码/DDL/API 的实现冲突
- 数据一致性风险
- 对齐问题清单

---

如果未提供 PRD 内容，请询问用户提供。
