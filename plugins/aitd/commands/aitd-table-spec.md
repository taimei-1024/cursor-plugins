---
name: aitd-table-spec
description: 从 DDL/实体类/数据库提取表结构，生成格式化清单并校验命名规范
---

# 提取表结构

请使用 table-spec 技能提取表结构。

**使用方式**：
- `/aitd-table-spec <DDL 语句>`
- `/aitd-table-spec <Entity 类代码>`
- `/aitd-table-spec`

**输出内容**：
- 表级信息（用途、存储引擎、字符集）
- 字段明细表
- 索引清单
- 外键/关联关系
- 规范校验结果
- ER 图（多表时）

**支持输入**：
- DDL 语句（CREATE TABLE）
- Entity/DTO 类代码
- 表名（通过 describe_table）

---

如果未提供输入内容，请询问用户提供 DDL、Entity 类或表名。
