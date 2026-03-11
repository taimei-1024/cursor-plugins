---
name: aitd-api-contract
description: 生成 API 契约表格，对照接口设计规范校验
---

# 生成 API 契约表

请使用 design-outline 技能生成 API 契约表格。

**使用方式**：
- `/aitd-api-contract <Controller 代码>`
- `/aitd-api-contract <JSON 示例>`
- `/aitd-api-contract`

**输出内容**：
- 接口清单总览
- 每个接口的详情（路径、方法、参数、响应、错误码）
- 接口设计规范校验结果

---

如果未提供输入内容，请询问用户提供 Controller 代码、JSON 示例或 Swagger 文档。
