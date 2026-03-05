# Java 编码规范建议

本文件提供 Java 后端开发的编码规范建议，供评审时参考。团队可根据实际情况调整。

---

## 1. 命名规范

### 包命名
- 全小写，使用公司域名倒序
- 格式：`com.company.project.module`
- 示例：`com.taimeitech.pv.report.service`

### 类命名
- 大驼峰命名（PascalCase）
- 名词或名词短语

| 类型 | 命名规则 | 示例 |
|------|----------|------|
| 普通类 | 名词 | `ReportService`, `AdverseEventController` |
| 接口 | 形容词或名词 | `Serializable`, `ReportRepository` |
| 抽象类 | Abstract 前缀 | `AbstractE2BHandler` |
| 异常类 | Exception 后缀 | `ReportNotFoundException` |
| 枚举类 | 名词 | `ReportStatus`, `SeriousnessType` |
| 工具类 | Utils/Helper 后缀 | `MeddraUtils`, `E2BHelper` |

### 方法命名
- 小驼峰命名（camelCase）
- 动词或动词短语

| 类型 | 命名规则 | 示例 |
|------|----------|------|
| 获取单个对象 | get 前缀 | `getReportById()` |
| 获取多个对象 | list/find 前缀 | `listReports()`, `findByPatientId()` |
| 获取统计值 | count 前缀 | `countByStatus()` |
| 插入 | save/insert/add | `saveReport()` |
| 更新 | update/modify | `updateStatus()` |
| 删除 | delete/remove | `deleteReport()` |
| 判断 | is/has/can | `isSerious()`, `hasExpedited()` |

### 变量命名
- 小驼峰命名
- 有意义的名称，避免单字母（循环变量除外）

```java
// 好的命名
String safetyReportId;
List<AdverseEvent> adverseEventList;
int totalCount;

// 避免的命名
String s;
List<AdverseEvent> list;
int n;
```

### 常量命名
- 全大写，下划线分隔
- 示例：`MAX_ADVERSE_EVENTS`, `DEFAULT_PAGE_SIZE`

---

## 2. 代码结构规范

### 类结构顺序
```java
public class ReportService {
    // 1. 静态常量
    private static final int MAX_RETRY = 3;
    
    // 2. 静态变量
    private static Logger logger = LoggerFactory.getLogger(ReportService.class);
    
    // 3. 实例变量
    @Autowired
    private ReportRepository reportRepository;
    
    // 4. 构造方法
    public ReportService() {}
    
    // 5. 公共方法
    public Report getReportById(Long id) {}
    
    // 6. 私有方法
    private void validateReport(Report report) {}
}
```

### 方法长度
- 单个方法不超过 80 行
- 超过时考虑拆分为多个私有方法

### 类长度
- 单个类不超过 500 行
- 超过时考虑拆分职责

### 参数数量
- 方法参数不超过 5 个
- 超过时考虑使用对象封装

```java
// 不推荐
public void createReport(String safetyReportId, Long patientId, 
                         List<AdverseEvent> events, List<Drug> drugs,
                         String narrativeSummary, Date receiveDate) {}

// 推荐
public void createReport(CreateReportRequest request) {}
```

---

## 3. 注释规范

### 类注释
```java
/**
 * ICSR 报告服务
 * 
 * 提供安全报告的创建、查询、更新、提交等功能
 *
 * @author zhangsan
 * @date 2024-01-15
 */
public class ReportService {}
```

### 方法注释
```java
/**
 * 根据报告ID查询 ICSR 详情
 *
 * @param reportId 报告ID，不能为空
 * @return ICSR 详情，不存在时返回 null
 * @throws IllegalArgumentException 当 reportId 为空时抛出
 */
public Report getReportById(Long reportId) {}
```

### 代码注释
- 解释"为什么"，而不是"是什么"
- 复杂逻辑必须添加注释

```java
// 好的注释：解释业务逻辑
// 严重不良事件需要在15天内提交到监管机构
if (report.isSerious() && report.getReceiveDate().plusDays(15).isBefore(LocalDate.now())) {
    markAsExpedited(report);
}

// 不好的注释：描述代码本身
// 判断是否超过15天
if (report.isSerious() && report.getReceiveDate().plusDays(15).isBefore(LocalDate.now())) {
    markAsExpedited(report);
}
```

---

## 4. 异常处理规范

### 异常分类
| 类型 | 说明 | 处理方式 |
|------|------|----------|
| 业务异常 | 可预期的业务错误 | 自定义异常，返回错误码 |
| 系统异常 | 不可预期的系统错误 | 记录日志，返回通用错误 |
| 参数异常 | 参数校验失败 | 返回具体的校验错误信息 |

### 异常处理原则
```java
// 1. 不要捕获 Exception，要捕获具体异常
try {
    // ...
} catch (IOException e) {
    // 处理 IO 异常
} catch (SQLException e) {
    // 处理 SQL 异常
}

// 2. 不要吞掉异常
try {
    // ...
} catch (Exception e) {
    // 错误：吞掉异常
}

try {
    // ...
} catch (Exception e) {
    // 正确：记录日志或重新抛出
    log.error("E2B导出失败", e);
    throw new BusinessException("E2B导出失败", e);
}

// 3. finally 中不要 return
```

### 自定义异常
```java
public class BusinessException extends RuntimeException {
    private String errorCode;
    private String errorMessage;
    
    public BusinessException(String errorCode, String errorMessage) {
        super(errorMessage);
        this.errorCode = errorCode;
        this.errorMessage = errorMessage;
    }
}
```

---

## 5. 日志规范

### 日志级别
| 级别 | 使用场景 |
|------|----------|
| ERROR | 系统错误，需要立即处理 |
| WARN | 警告信息，可能存在问题 |
| INFO | 重要业务流程，关键操作 |
| DEBUG | 调试信息，开发环境使用 |

### 日志格式
```java
// 使用占位符，避免字符串拼接
log.info("ICSR提交成功, reportId={}, safetyReportId={}", reportId, safetyReportId);

// 异常日志要包含堆栈
log.error("E2B生成失败, reportId={}", reportId, e);

// 敏感信息脱敏
log.info("患者信息更新, patientInitials={}", maskPatientInfo(initials));
```

### 日志内容
- 包含关键业务标识（报告ID、安全报告ID等）
- 包含操作结果
- 敏感信息脱敏（患者信息、报告人信息）

---

## 6. 其他规范

### 空值处理
```java
// 使用 Optional 处理可能为空的返回值
public Optional<Report> findById(Long id) {
    return Optional.ofNullable(reportRepository.findById(id));
}

// 使用 Objects.requireNonNull 校验参数
public void process(Report report) {
    Objects.requireNonNull(report, "report cannot be null");
}
```

### 集合处理
```java
// 返回空集合而不是 null
public List<AdverseEvent> listAdverseEvents(Long reportId) {
    List<AdverseEvent> events = eventRepository.findByReportId(reportId);
    return events != null ? events : Collections.emptyList();
}

// 使用 CollectionUtils 判断集合
if (CollectionUtils.isEmpty(adverseEvents)) {
    return;
}
```

### 字符串处理
```java
// 使用 StringUtils 判断字符串
if (StringUtils.isBlank(safetyReportId)) {
    return;
}

// 使用 StringBuilder 拼接字符串
StringBuilder sb = new StringBuilder();
for (String term : meddraTerms) {
    sb.append(term).append(",");
}
```
