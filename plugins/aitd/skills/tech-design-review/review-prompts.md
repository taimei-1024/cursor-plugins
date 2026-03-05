# 技术设计评审 - 标准提示词模板

本文件提供不同需求类型的评审提示词模板，用户可以直接复制使用。

---

## 新功能开发评审

```
请对以下技术设计进行评审：

## 基本信息
- Jira Key: {PVS-XXX}
- 技术设计文档: {Confluence 页面 URL}
- 需求类型: 新功能开发

## 评审要求
请按照评审检查清单，重点关注：
1. 设计是否完整覆盖需求和验收标准
2. 架构设计是否合理，分层是否清晰
3. 接口设计是否符合 RESTful 规范
4. 数据模型设计是否合理
5. 是否考虑了安全性和性能

## 补充信息（可选）
- 系统架构文档: {URL}
- 需要跳过的检查类别: {类别名称}
```

---

## 功能迭代评审

```
请对以下技术设计进行评审：

## 基本信息
- Jira Key: {PVS-XXX}
- 技术设计文档: {Confluence 页面 URL}
- 需求类型: 功能迭代

## 代码信息
- 相关表名: {tm_report, tm_adverse_event, tm_drug}
- 代码路径: {src/main/java/com/taimeitech/pv/report/}

## 评审要求
请按照评审检查清单，重点关注：
1. 设计是否完整覆盖需求和验收标准
2. 新设计与现有代码的兼容性
3. 数据库变更是否向后兼容
4. 是否需要数据迁移
5. 对现有功能的影响范围

## 补充信息（可选）
- 历史设计文档: {URL}
- 系统架构文档: {URL}
```

---

## 技术优化评审

```
请对以下技术设计进行评审：

## 基本信息
- Jira Key: {PVS-XXX}
- 技术设计文档: {Confluence 页面 URL}
- 需求类型: 技术优化

## 代码信息
- 相关表名: {tm_report, tm_adverse_event}
- 代码路径: {src/main/java/com/taimeitech/pv/report/}

## 优化背景
- 当前问题: {描述当前存在的问题，如 ICSR 生成性能瓶颈、E2B 导出超时等}
- 优化目标: {描述期望达到的效果}

## 评审要求
请按照评审检查清单，重点关注：
1. 优化方案是否能解决当前问题
2. 优化方案的技术可行性
3. 对现有功能的影响
4. 是否引入新的风险
5. 回滚方案是否可行

## 补充信息（可选）
- 性能数据: {当前 RT、QPS 等}
- 历史设计文档: {URL}
```

---

## 多工程评审

```
请对以下技术设计进行评审：

## 基本信息
- Jira Key: {PVS-XXX}
- 技术设计文档: {Confluence 页面 URL}
- 需求类型: {新功能开发/功能迭代/技术优化}

## 涉及工程
本次设计涉及以下多个工程：

### 工程 1: {pvs-report}
- 代码路径: {pvs-report/src/main/java/com/taimeitech/pv/report/}
- 相关表名: {tm_report, tm_adverse_event, tm_drug}

### 工程 2: {pvs-gateway}
- 代码路径: {pvs-gateway/src/main/java/com/taimeitech/pv/gateway/}
- 相关表名: {tm_e2b_message, tm_ack_record}

### 工程 3: {pvs-coding}
- 代码路径: {pvs-coding/src/main/java/com/taimeitech/pv/coding/}
- 相关表名: {tm_meddra_term, tm_whodrug}

## 评审要求
请按照评审检查清单，重点关注：
1. 跨服务调用的接口设计
2. 分布式事务处理方案
3. 服务间的依赖关系
4. 各服务的职责边界
5. 异常情况下的数据一致性
```

---

## 快速评审（简化版）

```
快速评审：
- Jira: {PVS-XXX}
- 设计文档: {URL}
- 类型: {新功能/迭代/优化}
- 表名: {tm_report, tm_adverse_event}（迭代/优化时填写）
- 代码: {path}（迭代/优化时填写）
```

---

## 使用说明

1. 根据需求类型选择对应的模板
2. 替换 `{...}` 中的占位符为实际值
3. 可选信息根据实际情况填写或删除
4. 复制完整内容到 Cursor 中发送
