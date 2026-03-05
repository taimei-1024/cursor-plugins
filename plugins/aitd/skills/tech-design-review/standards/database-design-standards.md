# 数据库设计规范建议

本文件提供 MySQL 数据库设计规范建议，供评审时参考。

---

## 1. 表命名规范

### 基本规则
- 全小写，单词间用下划线分隔
- 使用有意义的英文单词
- 表名使用单数形式

### 命名格式
```
{业务模块}_{表名}
```

### 示例
| 模块 | 表名 | 说明 |
|------|------|------|
| 报告 | tm_report | ICSR 主表 |
| 报告 | tm_adverse_event | 不良事件表 |
| 报告 | tm_drug | 可疑药品表 |
| 报告 | tm_reporter | 报告人表 |
| 报告 | tm_patient | 患者信息表 |
| 编码 | tm_meddra_term | MedDRA 术语表 |
| 编码 | tm_whodrug | WHODrug 编码表 |

### 避免的命名
```sql
-- 不推荐
CREATE TABLE Report;        -- 大写
CREATE TABLE reports;       -- 复数
CREATE TABLE tbl_report;    -- 无意义前缀
CREATE TABLE t_report;      -- 无意义前缀

-- 推荐
CREATE TABLE tm_report;
```

---

## 2. 字段命名规范

### 基本规则
- 全小写，单词间用下划线分隔
- 使用有意义的英文单词
- 避免使用 MySQL 保留字

### 常用字段命名
| 字段类型 | 命名规则 | 示例 |
|----------|----------|------|
| 主键 | id | id |
| 外键 | {关联表}_id | patient_id, drug_id |
| 创建时间 | create_time / created_at | create_time |
| 更新时间 | update_time / updated_at | update_time |
| 创建人 | create_by / creator | create_by |
| 更新人 | update_by / updater | update_by |
| 状态 | status | status |
| 删除标记 | is_deleted / deleted | is_deleted |
| 排序 | sort / sort_order | sort_order |
| 备注 | remark / memo | remark |

### 布尔字段
- 使用 is_ 前缀
- 示例：is_deleted, is_serious, is_expedited

---

## 3. 字段类型选择

### 整数类型
| 类型 | 范围 | 使用场景 |
|------|------|----------|
| TINYINT | -128 ~ 127 | 状态、类型、布尔值 |
| SMALLINT | -32768 ~ 32767 | 小范围数值 |
| INT | -21亿 ~ 21亿 | 常规数量 |
| BIGINT | 很大 | 大数值 |

### 字符串类型
| 类型 | 使用场景 | 说明 |
|------|----------|------|
| CHAR(n) | 固定长度 | 如：MedDRA 代码、国家代码 |
| VARCHAR(n) | 可变长度 | 大多数字符串字段 |
| TEXT | 大文本 | 病例叙述、备注 |

### VARCHAR 长度建议
| 场景 | 长度 |
|------|------|
| UUID 主键 | VARCHAR(36) 或 CHAR(36) |
| 安全报告ID | VARCHAR(100) |
| MedDRA PT 术语 | VARCHAR(200) |
| 药品名称 | VARCHAR(500) |
| 患者姓名缩写 | VARCHAR(50) |
| 批号 | VARCHAR(100) |
| 病例叙述 | TEXT |

### 时间类型
| 类型 | 使用场景 |
|------|----------|
| DATETIME | 业务时间（报告日期、发生日期） |
| TIMESTAMP | 自动更新时间 |
| DATE | 只需要日期（出生日期、死亡日期） |

### 金额/剂量类型
```sql
-- 推荐：使用 DECIMAL
dose_amount DECIMAL(12,4) COMMENT '剂量数值'

-- 或使用 BIGINT 存储最小单位
dose_amount BIGINT COMMENT '剂量数值，单位：最小单位'
```

---

## 4. 主键设计

### 框架默认：UUID

框架默认使用 UUID 作为主键，无需在技术设计中特别说明：

```sql
CREATE TABLE tm_report (
    id VARCHAR(36) NOT NULL COMMENT '主键ID (UUID)',
    ...
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 其他主键类型（如有特殊需求）

如需使用其他主键类型，需在技术设计中说明理由：

| 类型 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| UUID（默认） | 全局唯一、无需协调 | 无序、占空间 | 大多数场景 |
| 自增 BIGINT | 简单、有序 | 分库分表困难 | 单库单表、对顺序有要求 |
| 雪花算法 | 有序、全局唯一 | 依赖时钟 | 需要有序ID的分布式场景 |

### 业务主键
```sql
-- 安全报告ID作为业务主键（唯一索引）
safety_report_id VARCHAR(100) NOT NULL COMMENT '安全报告ID',
UNIQUE KEY uk_safety_report_id (safety_report_id)
```

---

## 5. 索引设计

### 索引命名规范
| 类型 | 命名格式 | 示例 |
|------|----------|------|
| 主键 | pk_{表名} | pk_tm_report |
| 唯一索引 | uk_{字段名} | uk_safety_report_id |
| 普通索引 | idx_{字段名} | idx_patient_id |
| 联合索引 | idx_{字段1}_{字段2} | idx_tenant_status |

### 索引设计原则
1. **选择性高的字段优先**
   - 选择性 = 不重复值数量 / 总行数
   - 选择性越高，索引效果越好

2. **联合索引最左前缀**
   ```sql
   -- 索引 idx_tenant_status_time (tenant_id, status, create_time)
   -- 可以使用索引
   WHERE tenant_id = 1
   WHERE tenant_id = 1 AND status = 1
   WHERE tenant_id = 1 AND status = 1 AND create_time > '2024-01-01'
   
   -- 无法使用索引
   WHERE status = 1
   WHERE create_time > '2024-01-01'
   ```

3. **覆盖索引**
   ```sql
   -- 查询字段都在索引中，避免回表
   SELECT tenant_id, status FROM tm_report WHERE tenant_id = 1
   -- 索引：idx_tenant_status (tenant_id, status)
   ```

### 索引数量限制
- 单表索引数量不超过 5 个
- 联合索引字段数不超过 5 个

### 避免的索引
```sql
-- 不要在低选择性字段上建索引
INDEX idx_status (status)  -- 状态值只有几种

-- 不要在频繁更新的字段上建索引
INDEX idx_update_time (update_time)
```

---

## 6. 表设计规范

### 必备字段
```sql
CREATE TABLE tm_report (
    id VARCHAR(36) NOT NULL COMMENT '主键ID (UUID)',
    tenant_id VARCHAR(36) NOT NULL COMMENT '租户ID',
    project_id VARCHAR(36) NOT NULL COMMENT '项目ID',
    -- 业务字段...
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    create_by VARCHAR(36) COMMENT '创建人ID',
    update_by VARCHAR(36) COMMENT '更新人ID',
    is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '是否删除：0-否，1-是',
    PRIMARY KEY (id),
    KEY idx_tenant_project (tenant_id, project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ICSR安全报告表';
```

### 字段约束
```sql
-- NOT NULL：尽量设置，避免 NULL 值
safety_report_id VARCHAR(100) NOT NULL COMMENT '安全报告ID'

-- DEFAULT：设置合理的默认值
status TINYINT NOT NULL DEFAULT 0 COMMENT '报告状态'

-- COMMENT：必须添加注释
receive_date DATE COMMENT '接收日期'
```

### 字符集
- 使用 utf8mb4，支持特殊字符和多语言
- 排序规则：utf8mb4_general_ci

---

## 7. SQL 编写规范

### SELECT 规范
```sql
-- 不要使用 SELECT *
SELECT * FROM tm_report;  -- 不推荐

SELECT id, safety_report_id, status, receive_date FROM tm_report;  -- 推荐

-- 避免在 WHERE 中对字段进行函数操作
WHERE DATE(receive_date) = '2024-01-15'  -- 不推荐，无法使用索引
WHERE receive_date >= '2024-01-15' AND receive_date < '2024-01-16'  -- 推荐
```

### UPDATE/DELETE 规范
```sql
-- 必须带 WHERE 条件
UPDATE tm_report SET status = 1;  -- 危险！

UPDATE tm_report SET status = 1 WHERE id = 'xxx';  -- 正确

-- 大批量更新分批执行
```

### JOIN 规范
```sql
-- 小表驱动大表
SELECT r.* FROM tm_report r
INNER JOIN tm_patient p ON r.patient_id = p.id
WHERE p.sex = 'MALE';

-- 避免过多 JOIN，不超过 3 个表
```

### 事务规范
- 事务尽量短小
- 避免在事务中进行 RPC 调用
- 大批量操作分批提交

---

## 8. 分表策略

### 分表时机
- 单表数据量超过 500 万行
- 单表大小超过 2GB

### 分表方式
| 方式 | 说明 | 适用场景 |
|------|------|----------|
| 按时间 | tm_report_202401, tm_report_202402 | 历史报告归档 |
| 按租户 | tm_report_tenant_001 | 大租户隔离 |
| 按 ID 取模 | tm_report_0, tm_report_1 | 均匀分布的数据 |

### 分表命名
```
{表名}_{分表规则}
tm_report_202401
tm_report_tenant_001
tm_report_0
```
