# STEP装配层级解析方案

> 创建日期: 2025-12-09  
> 状态: 已验证可行，待实现  
> 优先级: 高

---

## 一、问题描述

### 现象
在处理**产品总图**（如"E-CW3T-VIO35挖机压实轮VIO35连接器"）时，BOM表中的子装配体（如"E-CW3T-01固定座组件"、"E-CW3T-02滚轮组件"）无法匹配到GLB中的3D零件。

### 用户反馈
> "我们代码在识别产品总图的时候，实际拿到的零件名称是有问题的。并不是他实际SolidWorks看到的样子...这就导致我们完全没办法匹配"

### 影响范围
- 产品总图的BOM-3D匹配失败
- 子装配体无法高亮显示
- 装配说明书生成不完整

---

## 二、问题分析

### 2.1 SolidWorks中的真实结构
```
E-CW3T-VIO35挖机压实轮VIO35连接器（顶层产品）
├── E-CW3T-01固定座组件<1>      ← 子装配体
│   ├── E-CW3T-01-01-Q355B方形板-机加
│   ├── E-CW3T-01-02-Q355B侧板
│   └── ...
├── E-CW3T-02滚轮组件<1>        ← 子装配体  
│   ├── E-CW3T-02-01-Q355B卷圆板
│   └── ...
├── E-CW3T-VIO35-01连接器总成    ← 子装配体
└── 各种螺栓、垫圈...
```

### 2.2 我们代码拿到的结构（被"拍平"了）
```
world
├── NAUO1 (空节点，没有geometry)  ← 丢失了"固定座组件"名称
├── NAUO2 (空节点，没有geometry)  ← 丢失了"滚轮组件"名称
├── NAUO4 (空节点，没有geometry)  ← 丢失了"连接器总成"名称
├── NAUO3 → E-CW3T-03-NM400耐磨刀板
├── NAUO44 → E-CW3T-02-01-Q355B卷圆板  ← 这是滚轮组件内的零件！
├── NAUO80 → E-CW3T-01-01-Q355B方形板  ← 这是固定座组件内的零件！
└── ...等85个独立零件
```

### 2.3 根本原因

**trimesh/cascadio库在加载STEP文件时：**
- ✅ 保留了geometry名称（零件名）
- ❌ 但子装配体节点变成了空的NAUO节点（NAUO1、NAUO2等）
- ❌ 节点名使用STEP内部ID，而不是产品名称（"固定座组件"）
- ❌ 装配层级关系丢失

**导致的问题：**
- BOM表期望匹配 "E-CW3T-01固定座组件"
- 但GLB里只有底层零件 "E-CW3T-01-01-Q355B方形板"
- 完全无法直接匹配！

---

## 三、解决方案

### 3.1 方案概述

**通过正则表达式直接解析STEP文本文件**，提取完整的装配层级结构，无需安装pythonocc-core。

### 3.2 技术原理

STEP文件中的关键实体：

```
1. PRODUCT - 产品定义，包含人类可读的名称
   #10364 = PRODUCT ( 'E-CW3T-VIO35挖机压实轮VIO35', ... )

2. PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE - 链接到PRODUCT
   #1078 = PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE ( '任何', '', #10364, ... )

3. PRODUCT_DEFINITION - 产品定义实例
   #20466 = PRODUCT_DEFINITION ( '未知', '', #1078, ... )

4. NEXT_ASSEMBLY_USAGE_OCCURRENCE (NAUO) - 定义装配关系
   #24359 = NEXT_ASSEMBLY_USAGE_OCCURRENCE ( 'NAUO1', ' ', ' ', #20466, #14913, $ )
                                              ^名称     ^描述    ^父PD    ^子PD
```

**解析链条：**
```
NAUO → parent_pd/child_pd → PRODUCT_DEFINITION → PDF → PRODUCT(名称)
```

### 3.3 验证结果

已创建测试脚本验证方案可行性：

| 测试项 | 结果 |
|--------|------|
| 解析STEP装配层级 | ✅ 成功 - 解析出4个装配体，88个NAUO关系 |
| 识别子装配体 | ✅ 成功 - 正确识别E-CW3T-01、E-CW3T-02、E-CW3T-VIO35-01 |
| 零件名称匹配GLB | ✅ 成功 - 85.7%匹配率（未匹配的都是子装配体本身） |
| NAUO节点映射 | ✅ 成功 - NAUO1/2/4 正确指向子装配体 |

**解析出的层级结构：**
```json
{
  "hierarchy": {
    "E-CW3T-VIO35挖机压实轮VIO35": [
      "E-CW3T-01固定座组件",
      "E-CW3T-02滚轮组件",
      "E-CW3T-VIO35-01连接器总成",
      "E-CW3T-03-NM400耐磨刀板",
      "各种螺栓垫圈..."
    ],
    "E-CW3T-01固定座组件": [
      "E-CW3T-01-01-Q355B方形板",
      "E-CW3T-01-02-Q355B侧板"
    ]
  }
}
```

---

## 四、实现计划

### 4.1 需要创建的文件

#### 1. `core/step_hierarchy_parser.py` - STEP层级解析模块

核心功能：
- `parse_step_hierarchy(step_file_path)` - 解析STEP文件返回层级结构
- 提取PRODUCT、PRODUCT_DEFINITION、NAUO等实体
- 建立完整的父子关系映射

**参考代码已存在：** `backend/test_step_hierarchy.py`

### 4.2 需要修改的文件

#### 1. `processors/file_processor.py`

修改 `_convert_with_trimesh()` 方法：
- 在转换STEP为GLB时，同时调用 `step_hierarchy_parser` 解析层级
- 将层级信息保存到 `{project}/step_assembly_hierarchy.json`

#### 2. BOM匹配逻辑相关文件

修改匹配逻辑：
- 当BOM项是组件（子装配体）时，从层级信息中查找其包含的零件
- 将这些零件的geometry作为该组件的3D零件列表

### 4.3 数据流

```
STEP文件
    ↓
step_hierarchy_parser.parse_step_hierarchy()
    ↓
step_assembly_hierarchy.json (层级结构)
    ↓
BOM匹配时：
  - 如果BOM项是组件 → 查找层级中的子零件 → 匹配GLB geometry
  - 如果BOM项是零件 → 直接匹配GLB geometry
```

---

## 五、现有测试代码

### 5.1 测试脚本位置

- `backend/test_step_hierarchy.py` - STEP层级解析测试
- `backend/test_hierarchy_matching.py` - 层级与GLB匹配验证

### 5.2 测试数据

- STEP文件：`output/03.05.20.0005E-CW3T-VIO35挖机压实轮VIO35连接器/step_files/`
- 生成的层级JSON：`output/03.05.20.0005E-CW3T-VIO35挖机压实轮VIO35连接器/step_assembly_hierarchy.json`

### 5.3 核心正则表达式

```python
# PRODUCT定义
product_pattern = r"#(\d+)\s*=\s*PRODUCT\s*\(\s*'([^']*)'[^)]*\)"

# PRODUCT_DEFINITION
prod_def_pattern = r"#(\d+)\s*=\s*PRODUCT_DEFINITION\s*\(\s*'[^']*'\s*,\s*'[^']*'\s*,\s*#(\d+)"

# PRODUCT_DEFINITION_FORMATION (含 _WITH_SPECIFIED_SOURCE 变体)
pdf_pattern = r"#(\d+)\s*=\s*PRODUCT_DEFINITION_FORMATION[_A-Z]*\s*\(\s*'[^']*'\s*,\s*'[^']*'\s*,\s*#(\d+)"

# NAUO装配关系
nauo_pattern = r"#(\d+)\s*=\s*NEXT_ASSEMBLY_USAGE_OCCURRENCE\s*\(\s*'([^']*)'\s*,\s*'[^']*'\s*,\s*'[^']*'\s*,\s*#(\d+)\s*,\s*#(\d+)"
```

---

## 六、注意事项

1. **编码问题**：STEP文件的中文可能是GB2312/GBK编码，解析时用 `errors='ignore'`
2. **名称匹配**：需要处理全角/半角字符、空格等差异
3. **子装配体识别**：hierarchy字典的key就是子装配体，它们本身没有geometry
4. **NAUO映射**：GLB中的NAUO1、NAUO2等节点通过nauos列表可映射到真实产品名称

---

## 七、预期效果

实现后：
- ✅ BOM中的"E-CW3T-01固定座组件"可以匹配到其包含的所有零件
- ✅ 点击组件时，高亮该组件下所有零件
- ✅ 装配说明书能正确显示组件级别的装配步骤
