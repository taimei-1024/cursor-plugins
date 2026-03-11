# Draw.io XML 规范与样式字典

## 1. XML 规范

### 1.1 基础结构与约束

```xml
<mxfile>
  <diagram name="Page-1" id="page1">
    <mxGraphModel dx="800" dy="600" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="850" pageHeight="600" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

**mxGraphModel 属性**：

| 属性 | 说明 | 推荐值 |
|------|------|--------|
| dx, dy | 画布偏移 | 按复杂度自适应（推荐 800x600） |
| grid | 启用网格 | 1 |
| gridSize | 网格大小 | 10 |
| guides | 辅助线 | 1 |
| tooltips | 提示 | 1 |
| connect | 连接功能 | 1 |
| arrows | 箭头 | 1 |
| fold | 折叠功能 | 1 |
| page | 页面视图 | 1 |
| pageScale | 页面缩放 | 1 |
| pageWidth | 页面宽度 | 按复杂度自适应（推荐 850） |
| pageHeight | 页面高度 | 按复杂度自适应（推荐 600） |
| math | 数学公式 | 0 |
| shadow | 阴影 | 0 |

- **ID 规则**：从 "2" 开始递增，"0"/"1" 保留给 root
- **parent 规则**：顶层元素 parent="1"，子元素 parent 指向容器 ID
- **mxCell 不能嵌套**：所有 mxCell 必须是兄弟节点，edges 不嵌套在节点内
- 描述文本单行压缩，禁止 XML 注释

### 1.2 节点与连线

**节点（vertex）**：

```xml
<mxCell id="2" value="文本" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1">
  <mxGeometry x="100" y="100" width="120" height="60" as="geometry"/>
</mxCell>
```

必须属性：id（唯一）、value（文本）、style（见第 2 节）、vertex="1"、parent（容器 ID）

**连线（edge）**：

```xml
<mxCell id="3" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;" edge="1" parent="1" source="2" target="4">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

必须属性：edge="1"、source/target（端点 ID）；value 为可选标签

**自由连线**（无 source/target，如时序图箭头）：

```xml
<mxGeometry relative="1" as="geometry">
  <mxPoint x="140" y="120" as="sourcePoint"/>
  <mxPoint x="380" y="120" as="targetPoint"/>
</mxGeometry>
```

**显式路径点**（跨容器连线必须使用）：

```xml
<Array as="points">
  <mxPoint x="200" y="50"/>
</Array>
```

### 1.3 容器模式

架构图分层、泳道图角色均使用此模式。

```xml
<mxCell id="lane1" value="容器标题" style="swimlane;startSize=30;" vertex="1" parent="1">
  <mxGeometry x="40" y="40" width="500" height="200" as="geometry"/>
</mxCell>
<mxCell id="child1" value="子节点" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="lane1">
  <mxGeometry x="20" y="40" width="120" height="40" as="geometry"/>
</mxCell>
```

- 子节点 parent 指向容器 ID，连线 parent="1"
- 可加 `container=1;collapsible=0;` 禁止折叠

**分组（Group）**：style="group" + connectable="0"，用于视觉聚合但不作为布局容器

### 1.4 表格与图层

**表格**：

```xml
<mxCell id="table1" style="shape=table;startSize=30;container=1;collapsible=1;childLayout=tableLayout;fixedRows=1;rowLines=0;fontStyle=1;align=center;" vertex="1" parent="1">
  <mxGeometry x="100" y="100" width="180" height="120" as="geometry"/>
</mxCell>
<mxCell id="row1" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=0;fillColor=none;collapsible=0;dropTarget=0;points=[0,0.5,1,0.5];portConstraint=eastwest;" vertex="1" parent="table1">
  <mxGeometry y="30" width="180" height="30" as="geometry"/>
</mxCell>
```

**图层**：自定义图层 parent="0"，元素 parent 指向图层 ID

```xml
<mxCell id="layer2" value="图层2" style="locked=0;" parent="0"/>
<mxCell id="elem1" value="元素" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="layer2">
  <mxGeometry x="100" y="100" width="120" height="60" as="geometry"/>
</mxCell>
```

## 2. 样式字典

### 2.1 形状样式

| 形状 | style 属性 | 适用场景 |
|------|-----------|----------|
| 矩形 | `rounded=1;whiteSpace=wrap;html=1;` | 流程节点 |
| 菱形 | `rhombus;whiteSpace=wrap;html=1;` | 判断/决策 |
| 椭圆 | `ellipse;whiteSpace=wrap;html=1;` | 开始/结束 |
| 圆柱 | `shape=cylinder3;whiteSpace=wrap;html=1;` | 数据库 |
| 三角形 | `shape=triangle;whiteSpace=wrap;html=1;` | 方向指示 |
| 六边形 | `shape=hexagon;whiteSpace=wrap;html=1;` | 准备/预处理 |
| 平行四边形 | `shape=parallelogram;whiteSpace=wrap;html=1;` | 输入/输出 |
| 文档 | `shape=document;whiteSpace=wrap;html=1;` | 文档/报告 |
| 云 | `shape=cloud;whiteSpace=wrap;html=1;` | 外部系统/云服务 |
| 人物 | `shape=actor;whiteSpace=wrap;html=1;` | 用户/角色 |
| 便签 | `shape=note;whiteSpace=wrap;html=1;` | 注释/说明 |
| 卡片 | `shape=card;whiteSpace=wrap;html=1;` | 卡片元素 |

### 2.2 连线样式

**基础样式**：`edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeWidth=2;`

| 属性 | 可选值 | 说明 |
|------|--------|------|
| edgeStyle | orthogonalEdgeStyle, elbowEdgeStyle, entityRelationEdgeStyle | 路由方式 |
| endArrow | classic, open, oval, diamond, block, none | 终点箭头 |
| startArrow | classic, open, oval, diamond, block, none | 起点箭头 |
| curved | 0, 1 | 曲线连接 |
| dashed | 0, 1 | 虚线 |
| dashPattern | 如 "8 8" | 虚线图案 |

**锚点坐标**：

| 方向 | exitX/exitY | entryX/entryY |
|------|-------------|---------------|
| 上 | 0.5, 0 | 0.5, 0 |
| 下 | 0.5, 1 | 0.5, 1 |
| 左 | 0, 0.5 | 0, 0.5 |
| 右 | 1, 0.5 | 1, 0.5 |

锚点偏移：exitDx/exitDy/entryDx/entryDy（像素值）

### 2.3 通用属性

| 属性 | 说明 |
|------|------|
| fillColor / strokeColor | 填充色 / 边框色 |
| strokeWidth | 边框宽度 |
| fontColor / fontSize / fontStyle | 字体颜色 / 大小 / 0普通 1粗体 2斜体 |
| align / verticalAlign | 水平对齐 / 垂直对齐 |
| opacity | 0-100 |

### 2.4 配色参考

以下为可选参考，非强制，可根据图表内容自行调配：

| 用途 | fillColor | strokeColor |
|------|-----------|-------------|
| 开始/成功 | #d5e8d4 | #82b366 |
| 处理/步骤 | #dae8fc | #6c8ebf |
| 判断/决策 | #fff2cc | #d6b656 |
| 错误/警告 | #f8cecc | #b85450 |
| 外部系统 | #e1d5e7 | #9673a6 |
| 数据/存储 | #f5f5f5 | #666666 |
