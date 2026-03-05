# 接口设计规范建议

本文件提供 RESTful API 设计规范建议，供评审时参考。

> **说明**：本规范为参考性建议，技术设计中不要求写详细的参数定义、响应定义和错误码定义。

---

## 1. URL 设计规范

### 基本原则
- 使用名词复数表示资源
- 使用小写字母和连字符
- 避免动词（动作由 HTTP 方法表示）

### URL 格式
```
/{resource}/{id}/{sub-resource}
```

> **注意**：URL 中的版本号（如 /v1/）为可选，团队可根据实际情况决定是否使用。

### 示例
| 操作 | HTTP 方法 | URL | 说明 |
|------|-----------|-----|------|
| 获取 ICSR 列表 | GET | /reports | 获取所有安全报告 |
| 获取单个 ICSR | GET | /reports/{id} | 获取指定安全报告 |
| 创建 ICSR | POST | /reports | 创建新安全报告 |
| 更新 ICSR | PUT | /reports/{id} | 全量更新安全报告 |
| 部分更新 | PATCH | /reports/{id} | 部分更新安全报告 |
| 删除 ICSR | DELETE | /reports/{id} | 删除安全报告 |
| 获取不良事件 | GET | /reports/{id}/adverse-events | 获取报告下的不良事件 |

### 避免的设计
```
# 不推荐
GET /getReports
POST /createReport
GET /report/list
POST /report/delete/{id}

# 推荐
GET /reports
POST /reports
GET /reports
DELETE /reports/{id}
```

---

## 2. HTTP 方法使用

| 方法 | 语义 | 幂等性 | 安全性 | 使用场景 |
|------|------|--------|--------|----------|
| GET | 查询 | 是 | 是 | 获取资源 |
| POST | 创建 | 否 | 否 | 创建资源 |
| PUT | 全量更新 | 是 | 否 | 替换整个资源 |
| PATCH | 部分更新 | 否 | 否 | 更新部分字段 |
| DELETE | 删除 | 是 | 否 | 删除资源 |

### 幂等性设计（重要）

写操作需要考虑幂等性，防止网络重试导致重复提交：

```java
// POST 创建 ICSR - 幂等性设计方案

// 方案1：客户端生成唯一请求ID
POST /reports
{
    "requestId": "uuid-xxx",  // 幂等键
    "safetyReportId": "CN-TAIMEI-2024-00001",
    ...
}

// 方案2：服务端基于业务字段去重
// 如：同一安全报告ID不允许重复创建
```

---

## 3. 请求格式规范

### 请求头
```
Content-Type: application/json
Authorization: Bearer {token}
X-Request-Id: {uuid}  // 请求追踪ID
TM-Header-Tenant-Id: {tenantId}  // 租户ID
TM-Header-Project-Id: {projectId}  // 项目ID
```

### 请求体格式示例
```json
{
    "safetyReportId": "CN-TAIMEI-2024-00001",
    "reportType": "INITIAL",
    "adverseEvents": [
        {
            "meddraCode": "10019211",
            "term": "头痛",
            "seriousness": "NON_SERIOUS"
        }
    ],
    "patient": {
        "initials": "ZS",
        "age": 45,
        "sex": "MALE"
    }
}
```

---

## 4. 响应格式规范

框架已统一响应格式，接口开发时自动遵循：

### 统一响应结构
```json
{
    "code": "200",
    "message": "success",
    "data": {
        // 业务数据
    },
    "timestamp": 1705312800000,
    "traceId": "uuid-xxx"
}
```

### 成功响应示例
```json
// 查询单个资源
{
    "code": "200",
    "message": "success",
    "data": {
        "reportId": 12345,
        "safetyReportId": "CN-TAIMEI-2024-00001",
        "status": "SUBMITTED",
        "reportType": "INITIAL"
    }
}

// 查询列表（分页）
{
    "code": "200",
    "message": "success",
    "data": {
        "list": [...],
        "total": 100,
        "pageNum": 1,
        "pageSize": 20
    }
}
```

### 错误响应示例
```json
{
    "code": "400001",
    "message": "参数校验失败",
    "data": null,
    "errors": [
        {
            "field": "safetyReportId",
            "message": "安全报告ID不能为空"
        }
    ],
    "timestamp": 1705312800000,
    "traceId": "uuid-xxx"
}
```

---

## 5. 错误码规范（建议）

> **说明**：建议定义清晰的错误码体系，但非强制要求在技术设计中详细定义。

### 错误码格式建议
```
{HTTP状态码}{业务模块}{错误序号}
```

### 错误码分类示例
| 范围 | 说明 | 示例 |
|------|------|------|
| 200xxx | 成功 | 200000 |
| 400xxx | 客户端错误 | 400001 参数校验失败 |
| 401xxx | 认证错误 | 401001 Token 过期 |
| 403xxx | 权限错误 | 403001 无访问权限 |
| 404xxx | 资源不存在 | 404001 报告不存在 |
| 500xxx | 服务端错误 | 500001 系统繁忙 |

---

## 6. 分页规范

### 请求参数
```
GET /reports?pageNum=1&pageSize=20&status=SUBMITTED&sortBy=createTime&sortOrder=desc
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| pageNum | 页码，从1开始 | 1 |
| pageSize | 每页数量 | 20 |
| sortBy | 排序字段 | createTime |
| sortOrder | 排序方向 asc/desc | desc |

### 分页限制
- pageSize 最大值限制（建议 100）
- 大数据量场景考虑游标分页

---

## 7. 批量操作规范

批量接口需要设置数量限制，防止性能问题：

```java
// 批量创建 - 限制单次最多 100 条
POST /reports/batch
{
    "reports": [...],  // 最多 100 条
}

// 批量查询 - 限制单次最多 100 个ID
POST /reports/batch-query
{
    "ids": [...]  // 最多 100 个
}
```

---

## 8. 安全规范

以下安全措施由框架统一处理，无需在技术设计中体现：

- 认证：Bearer Token
- 接口权限控制
- 参数校验
- SQL 注入防护
- XSS 防护
- 敏感数据脱敏
- 审计日志记录
